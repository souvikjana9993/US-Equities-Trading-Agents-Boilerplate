from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters
import logging

logger = logging.getLogger("MCPManager")

def get_financial_mcp_client():
    """
    Initializes a connection to the 'fintools-mcp' server.
    This server provides additional tools like insider trading, 
    options data, and stock screening.
    """
    try:
        # We use 'uvx' to run the MCP server without manual installation
        params = StdioServerParameters(
            command="uvx",
            args=["fintools-mcp"],
            env={}
        )
        
        return MCPClient(lambda: stdio_client(params))
    except Exception as e:
        logger.error(f"Failed to initialize MCP Client: {e}")
        return None
