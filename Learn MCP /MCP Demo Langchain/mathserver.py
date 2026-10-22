from mcp.server.fastmcp import FastMCP

# What is Stdio and Transport?  
# Stdio is the standard input and output streams (stdin and stdout) of a process.
# Use Standard Input and Output to receive and send messages to tool function calls.
# Transport is the protocol used to communicate with the client.   

mcp = FastMCP("math")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtract two numbers"""
    return a - b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

@mcp.tool()
def divide(a: int, b: int) -> int:
    """Divide two numbers"""
    return a / b

if __name__ == "__main__":
    mcp.run(transport="stdio")