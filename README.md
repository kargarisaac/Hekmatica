# CryptoCurrency Agent

## Activate MCP servers for BAML Documentations

- Run the BAML MCP server
```bash
poetry run mcpdoc --urls BAMLDocs:https://docs.boundaryml.com/llms.txt \
  --transport sse \
  --port 8083 \
  --host localhost \
  --allowed-domains 'https://docs.boundaryml.com'
```

- Run the LangGraph MCP server
```bash
poetry run mcpdoc --urls LangGraphDocs:https://langchain-ai.github.io/langgraph/llms.txt \
  --transport sse \
  --port 8084 \
  --host localhost \
  --allowed-domains 'https://langchain-ai.github.io/'
```

- inspect the server and test:
```bash
npx @modelcontextprotocol/inspector
```

### Set MCP Servers on cursor
- Here is the content of the `mcp.json` file on cursor:
```json
{
  "mcpServers": {
    "baml-docs": {
      "url": "http://localhost:8083/sse"
    },
    "langgraph-docs": {
      "url": "http://localhost:8084/sse"
    }
  }
}
```

- Make sure you have the server running in the terminal and enabled in cursor. Put the cursor mode in `Agent` and make sure you use the cursorrules in the prompt for the agent. Then it will use them to get the context.

### cursorrules
Here are cursorrules for BAML and LangGraph:
```txt
# BAML
When asked about BAML, use the "baml-docs" MCP server:
- Call the list_doc_sources tool to find available documentation sources.
- Call the fetch_docs tool to open the BAML docs index (baml_llms.txt).
- Examine the list of documentation topics for relevance.
- Call fetch_docs on the relevant documentation URL(s) to get details.
- Use the retrieved documentation content to answer the question.
```

```txt
When asked about LangGraph, use the "langgraph-docs" MCP server:
- Call the list_doc_sources tool to find available documentation sources.
- Call the fetch_docs tool to open the LangGraph docs index (https://langchain-ai.github.io/langgraph/llms.txt).
- Examine the list of documentation topics for relevance.
- Call fetch_docs on the relevant documentation URL(s) to get details.
- Use the retrieved documentation content to answer the question.
```

