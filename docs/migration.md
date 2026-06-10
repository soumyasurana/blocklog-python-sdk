# Migration & Integration Guides

If you already have a mature AI application, integrating Blocklog requires minimal code changes. This guide shows how to add Blocklog to existing projects.

## Existing Custom Python Agents

**Before:**
```python
def my_custom_tool(data: str) -> str:
    return "Processed " + data

def main_agent(input_data: str):
    print("Starting agent")
    result = my_custom_tool(input_data)
    print("Done")
    return result
```

**After (With Blocklog):**
```python
import blocklog
blocklog.init(api_key="blk_...")

@blocklog.tool
def my_custom_tool(data: str) -> str:
    return "Processed " + data

@blocklog.agent(name="main_agent")
def main_agent(input_data: str):
    print("Starting agent")
    result = my_custom_tool(input_data)
    
    with blocklog.decision(type="PROCESS", asset="data") as d:
        d.record_input(data=input_data)
        d.record_output(result=result)
        
    print("Done")
    return result
```

## LangChain Projects

Blocklog automatically hooks into LangChain using `client.instrument_langchain()`. 

**Before:**
```python
from langchain.llms import OpenAI
from langchain.chains import LLMChain

llm = OpenAI(temperature=0.9)
chain = LLMChain(llm=llm, prompt=prompt)
chain.run("example input")
```

**After (With Blocklog):**
```python
import blocklog
from langchain.llms import OpenAI
from langchain.chains import LLMChain

client = blocklog.init(api_key="blk_...")
client.instrument_langchain() # Automatically adds BlocklogLangChainCallbackHandler

llm = OpenAI(temperature=0.9)
chain = LLMChain(llm=llm, prompt=prompt)

# LangChain runs will now be automatically traced in Blocklog
chain.run("example input")
```

## LangGraph Projects

Similarly, for LangGraph, simply call the instrumentation hook:

```python
import blocklog

client = blocklog.init()
client.instrument_langgraph()

# Continue with normal LangGraph execution
```

## OpenAI Agents

If you use the official OpenAI Agents SDK, hook into the workflow:

```python
import blocklog

client = blocklog.init()
client.instrument_openai_agents()

# Your OpenAI client and agent usage remains identical.
```
