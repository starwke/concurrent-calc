# -*- coding: utf-8 -*-

# @Author  : wzdnzd
# @Time    : 2025-06-01

import concurrent.futures
from collections import defaultdict
from dataclasses import dataclass, field

import jieba

import utils
from logger import logger


@dataclass
class TableInfo(object):
    # 表名
    name: str

    # 列信息
    columns: list[dict] = field(default_factory=list)


@dataclass
class EnumRecord(object):
    # 所在表名
    table: str

    # 列名
    column: str

    # 列值
    value: str

    # 相似度
    similarity: float = 0.0


def jaccard(s1: set, s2: set) -> float:
    if not isinstance(s1, set) or not isinstance(s2, set):
        return 0.0
    elif s1 == s2:
        return 1.0

    # 交集
    c1 = len(s1.intersection(s2))

    # 并集
    c2 = len(s1.union(s2))

    return c1 / c2


def compute(words: set, record: EnumRecord) -> float:
    if not words or not record or not isinstance(record, EnumRecord):
        return 0.0

    segments = set(tokenize(text=record.value))
    return jaccard(s1=words, s2=segments)


def compute_str(words: set, col_val: str) -> float:
    if not words or not col_val or not isinstance(col_val, str):
        return 0.0

    segments = set(tokenize(text=col_val))
    return jaccard(s1=words, s2=segments)


def tokenize(text: str) -> list[str]:
    if not text or not isinstance(text, str):
        return []

    return jieba.cut(text)


def allocate(item: dict, data_type: str) -> tuple[TableInfo, list[EnumRecord]]:
    data_type = utils.trim(data_type)
    if not item or not isinstance(item, dict) or not data_type:
        return None, []

    columns = item.get("column_info", [])
    if not columns or not isinstance(columns, list):
        item["column_info"] = list()
        return None, []

    table_name = item.get("table_name", "")

    # 过滤出需要以及不需要计算的列
    necessaries, unnecessaries = [], []
    for column in columns:
        if not column or not isinstance(column, dict):
            logger.warning(f"无效的列信息: {column}")
            continue

        if column.get("data_format", "") == data_type:
            column_name = column.get("column_name", "")
            values = column.get("column_enum_value", [])
            if not values or not isinstance(values, list):
                continue

            for v in values:
                necessaries.append(EnumRecord(table=table_name, column=column_name, value=v))
        else:
            unnecessaries.append(column)

    return TableInfo(name=table_name, columns=unnecessaries), necessaries


def assign(tables: list[dict], data_type: str) -> tuple[dict[str, TableInfo], list[EnumRecord]]:
    if not tables or not isinstance(tables, list):
        return {}, []

    tasks = [[t, data_type] for t in tables]
    results = utils.multi_process_run(func=allocate, tasks=tasks)

    mappings, records = dict(), list()
    for t, r in results:
        if not t or not isinstance(t, TableInfo):
            continue

        mappings[t.name] = t
        records.extend(r)

    return mappings, records


def select(records: list[EnumRecord], top_k: int, data_type: str) -> TableInfo:
    if not records or not isinstance(records, list):
        logger.warning(f"候选列表无效，无需挑选前 {top_k} 个候选枚举值")
        return None

    table_name = records[0].table
    column_name, items = records[0].column, None

    if len(records) <= top_k:
        items = [x.value for x in records if x]
    else:
        # 按 similarity 由高到低排序
        records.sort(key=lambda x: -x.similarity)

        # 选取前 top_k
        items = [x.value for x in records[:top_k] if x]

    candidate = {"data_format": data_type, "column_name": column_name, "column_enum_value": items}
    return TableInfo(name=table_name, columns=[candidate])


@utils.calc_time
def retrieve_column_value_options_name(
        question: str, tables: list[dict], top_k: int = 10, data_type: str = "str", timeout: float = None
) -> list[dict]:
    text = utils.trim(question)
    if not text:
        raise ValueError("问题不能为空")

    if not tables or not isinstance(tables, list):
        raise ValueError("数据库表信息缺失，无法进行排序")

    if top_k <= 0:
        raise ValueError("top_k不能必须大于0")

    data_type = utils.trim(data_type)
    if not data_type:
        raise ValueError("必须知道需要被计算的列的数据类型")

    # 如果指定了超时时间，使用超时处理逻辑
    if timeout is not None and timeout > 0:
        try:
            # 使用ThreadPoolExecutor来实现超时控制
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                # 提交任务
                future = executor.submit(retrieve_common, question, tables, top_k)

                try:
                    # 等待结果，如果超时会抛出TimeoutError
                    result = future.result(timeout=timeout)
                    return result
                except concurrent.futures.TimeoutError:
                    # 超时了，取消任务。无法强制停止，仅标记为取消
                    future.cancel()
                    raise utils.TimeoutError(
                        func="_retrieve",
                        timeout=timeout,
                        count=len(tables) if tables else 0
                    )
        except utils.TimeoutError as e:
            # 超时情况：使用截断策略
            logger.warning(f"执行超时: {e}，将使用截断策略")
            return _truncate_column_values(tables=tables, top_k=top_k, data_type=data_type)

    # 无超时限制，正常执行逻辑
    return _retrieve(question, tables, top_k, data_type)


def _retrieve(question: str, tables: list[dict], top_k: int, data_type: str) -> list[dict]:
    """
    支持并行处理的列值选项检索函数
    智能检测是否在子进程中运行，避免嵌套多进程问题，并行处理
    """
    # 第一步：并行过滤出需要计算的目标（直接调用allocate，避免嵌套）
    if not tables or not isinstance(tables, list):
        return []

    tasks = [[t, data_type] for t in tables]
    results = utils.multi_process_run(func=allocate, tasks=tasks)

    mappings, records = dict(), list()
    for t, r in results:
        if not t or not isinstance(t, TableInfo):
            continue

        mappings[t.name] = t
        records.extend(r)

    if not records:
        return tables

    # 第二步：对 question 分词
    s1 = set(tokenize(question))
    jobs = [[s1, r] for r in records]

    # 第三步：并行计算 jaccard 相似度
    similarities = utils.multi_process_run(func=compute, tasks=jobs)

    # 第四步：按表名及列名进行分组
    groups = defaultdict(lambda: defaultdict(list))
    for i, r in enumerate(records):
        r.similarity = similarities[i]
        groups[r.table][r.column].append(r)

    # 第五步：对每个表每个字段并行排序并挑选出 top_k 个候选值
    tasks = [[items, top_k, data_type] for inner in groups.values() for items in inner.values()]
    infos = utils.multi_process_run(func=select, tasks=tasks)
    for info in infos:
        if not info or not isinstance(info, TableInfo):
            continue

        mappings[info.name].columns.extend(info.columns)

    # 将 mappings 转换成原 tables 数据结构并返回
    return [{"table_name": k, "column_info": v.columns} for k, v in mappings.items()]


def retrieve_common(question: str, table_column_info: list[dict], top_k: int = 10,
                    data_types: tuple = ('str', 'varchar')) -> list[dict]:
    if not table_column_info or not isinstance(table_column_info, list):
        return []
    s1 = set(tokenize(question))
    for cur_table_info in table_column_info:
        column_info = cur_table_info["column_info"]
        for cur_column_info in column_info:
            column_enum_value = cur_column_info.get("column_enum_value", [])
            data_format = cur_column_info.get("data_format", "")
            if len(column_enum_value) <= top_k:
                continue
            if len(column_enum_value) > top_k and data_format not in data_types:
                column_enum_value["column_enum_value"] = column_enum_value[:top_k]

            jobs = [[s1, col_val] for col_val in column_enum_value]
            results = utils.multi_process_run(func=compute_str, tasks=jobs)

            similarity_pairs = zip(column_enum_value, results)
            sorted_similarity_pairs = sorted(similarity_pairs, key=lambda x: -x[1])
            sorted_column_value = [x for x, _ in sorted_similarity_pairs][:top_k]
            cur_column_info["column_enum_value"] = sorted_column_value

    return table_column_info


def _truncate_column_values(tables: list[dict], top_k: int, data_type: str) -> list[dict]:
    """
    截断函数：直接返回每个指定data_type类型列的前top_k个取值，不进行相似度计算

    Args:
        tables: 数据库表信息列表
        top_k: 每列返回的最大值数量
        data_type: 目标数据类型

    Returns:
        截断后的表信息列表
    """
    if not tables or not isinstance(tables, list):
        return []

    result = []
    for table in tables:
        if not table or not isinstance(table, dict):
            continue

        table_name = table.get("table_name", "")
        columns = table.get("column_info", [])

        if not columns or not isinstance(columns, list):
            continue

        truncated_columns = []
        for column in columns:
            if not column or not isinstance(column, dict):
                continue

            # 只处理指定数据类型的列
            if column.get("data_format", "") == data_type:
                column_name = column.get("column_name", "")
                values = column.get("column_enum_value", [])

                if values and isinstance(values, list):
                    # 截断到前top_k个值
                    truncated_values = values[:top_k]
                    truncated_column = {
                        "data_format": data_type,
                        "column_name": column_name,
                        "column_enum_value": truncated_values
                    }
                    truncated_columns.append(truncated_column)
            else:
                # 非目标数据类型的列直接保留
                truncated_columns.append(column)

        if truncated_columns:
            result.append({
                "table_name": table_name,
                "column_info": truncated_columns
            })

    return result
