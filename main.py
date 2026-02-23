#Sample Server **********************************************************

from fastmcp import FastMCP
import random
import json


# Create a FastMCP server instance
mcp = FastMCP("Simple Calculator Server")

#Tool: Add two numbers
@mcp.tool("add_numbers")
def add_numbers(a: int, b: int) -> int:
    """Add two numbers and return the result.
    
    Args:
        a (int): The first number to add.
        b (int): The second number to add.
    
    Returns:
        int: The sum of the two numbers.
    """
    return a + b


#Tool: Generate a random number
@mcp.tool("generate_random_number")
def generate_random_number(min_value: int = 1, max_value: int = 100) -> int:
    """Generate a random number between the specified minimum and maximum values.

    Args:
        min_value (int, optional): The minimum value for the random number. Defaults to 1.
        max_value (int, optional): The maximum value for the random number. Defaults to 100.

    Returns:
        int: The random integer between min_value and max_value.
    """
    return random.randint(min_value, max_value)

#Resource: Get server information
@mcp.resource("info://server")
def get_server_info() -> str:
    """Get information about the server.

    Returns:
        str: A JSON string containing server information.
    """
    info = {
        "name": "Simple Calculator Server",
        "version": "1.0.0",
        "description": "A basic MCP server with math tools",
        "tools": ["add_numbers", "generate_random_number"],
        "authors": "Your Name"
    }
    return json.dumps(info, indent=2)

#Start the server
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)