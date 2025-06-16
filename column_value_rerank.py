from concurrent import futures
import logging


def retrieve_column_value_options_name(question, table_column_info, top_k=10):
    pass


def rerank(question: str, table_column_info: dict[dict[dict]], top_k: int = 10):
    try:
        with futures.ThreadPoolExecutor(max_workers=10) as executor:
            future = executor.submit(retrieve_column_value_options_name, question, table_column_info, top_k)
            retrieve_table_column_info = future.result(timeout=10)

    except futures.TimeoutError:
        logging.info("已经超时")
        retrieve_table_column_info = table_column_info


def jaccard(s1: set, s2: set) -> float:
    pass


if __name__ == '__main__':
    table_column_info = [
        {
            "table_name": "employment",
            "column_info": [
                {"data_format": "str", "column_name": "department", "column_enum_value": ["dev", "market", "it"]},
                {"data_format": "str", "column_name": "members", "column_enum_value": ["tom", "jerry", "kevin"]},
                {"data_format": "str", "column_name": "level", "column_enum_value": ["low", "middle", "high"]}]
        }, {
            "table_name": "employment",
            "column_info": [
                {"data_format": "str", "column_name": "department", "column_enum_value": ["dev", "market", "it"]},
                {"data_format": "str", "column_name": "members", "column_enum_value": ["tom", "jerry", "kevin"]},
                {"data_format": "str", "column_name": "level", "column_enum_value": ["low", "middle", "high"]}]
        }, {
            "table_name": "employment",
            "column_info": [
                {"data_format": "str", "column_name": "department", "column_enum_value": ["dev", "market", "it"]},
                {"data_format": "str", "column_name": "members", "column_enum_value": ["tom", "jerry", "kevin"]},
                {"data_format": "str", "column_name": "level", "column_enum_value": ["low", "middle", "high"]}]
        }
    ]
