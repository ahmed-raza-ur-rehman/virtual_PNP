"""MES (Manufacturing Execution System) client."""
from __future__ import annotations


class MESClient:
    def __init__(self, url: str):
        self.url = url

    def post_result(self, job_id: str, data: dict) -> bool:
        # placeholder HTTP POST
        return True

    def get_recipe(self, part_number: str) -> dict:
        return {}
