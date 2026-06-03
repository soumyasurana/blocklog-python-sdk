from __future__ import annotations

from uuid import uuid4

from blocklog import BlocklogClient


def main() -> None:
    client = BlocklogClient.from_env()
    handler = client.instrument_langchain()

    with client.session(agent_id="langchain-demo", source="langchain", workflow_id=uuid4()):
        run_id = uuid4()
        handler.on_chain_start(
            {"name": "demo-chain"},
            {"question": "What happened?"},
            run_id=run_id,
            metadata={"customer_id": "cus_demo_123"},
        )
        handler.on_tool_start(
            {"name": "search_docs"},
            "find refund policy",
            run_id=uuid4(),
            parent_run_id=run_id,
            metadata={"retrieval_index": "help-center-v1"},
        )
        handler.on_tool_end({"documents": 3}, run_id=uuid4(), parent_run_id=run_id)
        handler.on_llm_start({"name": "demo-llm"}, ["Summarize the refund policy"], run_id=uuid4(), parent_run_id=run_id)
        handler.on_llm_end({"output_text": "Refunds are approved after human review."}, run_id=uuid4(), parent_run_id=run_id)
        handler.on_chain_end({"answer": "Refunds require human review."}, run_id=run_id)


if __name__ == "__main__":
    main()
