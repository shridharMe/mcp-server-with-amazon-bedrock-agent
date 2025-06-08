import streamlit as st
import asyncio
import random
from asyncio import Semaphore
from mcp import StdioServerParameters
from InlineAgent.tools import MCPStdio
from InlineAgent.action_group import ActionGroup
from InlineAgent.agent import InlineAgent
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import lru_cache

# Constants
MAX_RETRIES = 5
REQUEST_LIMIT = 1
BACKOFF_BASE = 2
INITIAL_BACKOFF = 1

# Initialize rate limiting semaphore
request_semaphore = Semaphore(REQUEST_LIMIT)

class RateLimiter:
    def __init__(self, requests_per_second=1):
        self.requests_per_second = requests_per_second
        self.requests = []
        self.window_size = timedelta(seconds=1)

    async def acquire(self):
        now = datetime.now()
        # Remove old requests
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.window_size]
        
        if len(self.requests) >= self.requests_per_second:
            wait_time = (self.requests[0] + self.window_size - now).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.requests.append(now)

# Initialize rate limiter
rate_limiter = RateLimiter(requests_per_second=1)

# Set page configuration
st.set_page_config(
    page_title="DevOps  Assistant",
    page_icon="⏰",
    layout="wide"
)

@asynccontextmanager
async def create_mcp_client(server_params):
    """Safely create and manage MCP client lifecycle."""
    client = None
    try:
        client = await MCPStdio.create(server_params=server_params)
        yield client
    finally:
        if client:
            try:
                await client.cleanup()
            except Exception as e:
                st.error(f"Error during client cleanup: {str(e)}")

# Cache responses for 5 minutes
@lru_cache(maxsize=100)
def cache_key(input_text: str) -> str:
    timestamp = datetime.now().replace(second=0, microsecond=0)
    timestamp = timestamp.replace(minute=timestamp.minute - (timestamp.minute % 5))
    return f"{input_text}:{timestamp}"

async def process_query_with_cache(user_input: str):
    """Process query with caching to reduce API calls."""
    key = cache_key(user_input)
    
    # Try to get from cache first
    if hasattr(process_query_with_cache, 'cache') and key in process_query_with_cache.cache:
        return process_query_with_cache.cache[key]
    
    # If not in cache, make the API call
    result = await process_query_with_retry(user_input)
    
    # Store in cache
    if not hasattr(process_query_with_cache, 'cache'):
        process_query_with_cache.cache = {}
    process_query_with_cache.cache[key] = result
    
    return result

async def process_query_with_retry(user_input):
    """Process query with enhanced retry logic and rate limiting."""
    async with request_semaphore:
        await rate_limiter.acquire()
        for attempt in range(MAX_RETRIES):
            try:
                return await process_query(user_input)
            except Exception as e:
                if 'throttlingException' in str(e) and attempt < MAX_RETRIES - 1:
                    wait_time = (INITIAL_BACKOFF * (BACKOFF_BASE ** attempt)) + (random.random() * 0.5)
                    st.warning(f"Rate limit reached. Retrying in {wait_time:.2f} seconds... (Attempt {attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(wait_time)
                    continue
                raise

async def process_query(user_input):
    """Main query processing function with improved resource management."""
    # Define MCP parameters
    time_params = StdioServerParameters(
        command="podman",
        args=["run", "-i", "--rm", "mcp/time"],
    )
    
    maths_params = StdioServerParameters(
        command="uv",
        args=["run", "devops.py"],
    )
    jenkins_params = StdioServerParameters(
        command="uv",
        args=["run", "mcp-jenkins-server.py"],
    )

    # Use context managers for proper resource cleanup
    async with create_mcp_client(time_params) as time_client, \
               create_mcp_client(maths_params) as maths_client, \
               create_mcp_client(jenkins_params) as jenkins_client:
        
        # Create action group
        action_group = ActionGroup(
            name="TimeActionGroup",
            description="Helps user to do devops works and get current time and convert time and do simple maths",
            mcp_clients=[time_client, maths_client, jenkins_client],
        )

        # Create and invoke agent
        agent = InlineAgent(
            foundation_model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            instruction="""You are a devops assistant that is responsible for doing devops related task based on user queries. Also reponse should be in rich markdown format""",
            agent_name="time_agent",
            action_groups=[action_group],
        )

        return await agent.invoke(input_text=user_input)

def create_ui():
    """Create and manage the Streamlit UI components."""
    st.title("DevOps  Assistant")
    st.markdown("This assistant helps you with devops related queries and conversions.")

    # Input area
    user_input = st.text_area(
        "Enter your time-related query:",
        placeholder="",
        height=100
    )

    # Submit button and processing
    if st.button("Submit Query"):
        if not user_input:
            st.warning("Please enter a query first.")
            return

        with st.spinner("Processing your query..."):
            try:
                # Use cached version
                response = asyncio.run(process_query_with_cache(user_input))
                st.success("Response:")
                
                # Check if this is a Jenkins pipeline visualization request
                if "pipeline" in user_input.lower() and "visualization" in user_input.lower():
                    # Create markdown table header
                    table = "| Stage | Status | Duration |\n"
                    table += "|-------|--------|----------|\n"
                    
                    # Extract pipeline information from the response
                    if isinstance(response, str):
                        lines = response.split('\n')
                        for line in lines:
                            if any(status in line for status in ['✅', '❌', '🔄', '⏭️', '⛔', '❓']):
                                parts = line.split()
                                if len(parts) >= 2:
                                    status = parts[0]
                                    name = ' '.join(parts[1:-1]) if '(' in line else ' '.join(parts[1:])
                                    duration = parts[-1] if '(' in line else ''
                                    table += f"| {name} | {status} | {duration.strip('()')} |\n"
                    
                    # Add summary if available
                    if "Summary" in response:
                        summary = response[response.find("Summary"):]
                        table += f"\n{summary}"
                    
                    st.markdown(table)
                else:
                    st.write(response)
                    
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.error("Please try again in a few moments.")

    # Example queries
    with st.expander("Example Queries"):
        st.markdown("""
        **Jenkins Pipeline:**
        - Show me the pipeline visualization for build #14 of project-areo-build
        - Get the pipeline status for the latest build of project-areo-build
        - Trigger and monitor a new build for project-areo-build
        
        **Time Conversion:**
        - Convert 12:30pm to Europe/London timezone? My timezone is America/New_York
        - What time is it now in Tokyo?
        - Convert 3:45pm EST to PST
        """)

    # Footer
    st.markdown("---")
    st.markdown("Built with Streamlit and Amazon Bedrock")

if __name__ == "__main__":
    create_ui()
