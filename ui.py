import streamlit as st
import asyncio
from mcp import StdioServerParameters
from InlineAgent.tools import MCPStdio
from InlineAgent.action_group import ActionGroup
from InlineAgent.agent import InlineAgent

# Set page configuration
st.set_page_config(
    page_title="Time Conversion Assistant",
    page_icon="⏰",
    layout="wide"
)

# Add title and description
st.title("Time Conversion Assistant")
st.markdown("This assistant helps you with time-related queries and conversions.")

async def process_query(user_input):
    # Step 1: Define MCP stdio parameters
    server_params = StdioServerParameters(
        command="podman",
        args=["run", "-i", "--rm", "mcp/time"],
    )

    # Step 2: Create MCP Client
    time_mcp_client = await MCPStdio.create(server_params=server_params)

    try:
        # Step 3: Define an action group
        time_action_group = ActionGroup(
            name="TimeActionGroup",
            description="Helps user get current time and convert time.",
            mcp_clients=[time_mcp_client],
        )

        # Step 4: Invoke agent
        response = await InlineAgent(
            foundation_model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            instruction="""You are a friendly assistant that is responsible for resolving user queries. """,
            agent_name="time_agent",
            action_groups=[time_action_group],
        ).invoke(input_text=user_input)

        return response

    finally:
        await time_mcp_client.cleanup()

# Create the input area
user_input = st.text_area(
    "Enter your time-related query:",
    placeholder="Example: Convert 12:30pm to Europe/London timezone? My timezone is America/New_York",
    height=100
)

# Create a submit button
if st.button("Submit Query"):
    if user_input:
        with st.spinner("Processing your query..."):
            try:
                # Run the async function
                response = asyncio.run(process_query(user_input))
                
                # Display the response in a nice format
                st.success("Response:")
                st.write(response)
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
    else:
        st.warning("Please enter a query first.")

# Add some helpful examples
with st.expander("Example Queries"):
    st.markdown("""
    - Convert 12:30pm to Europe/London timezone? My timezone is America/New_York
    - What time is it now in Tokyo?
    - Convert 3:45pm EST to PST
    """)

# Add footer
st.markdown("---")
st.markdown("Built with Streamlit and Amazon Bedrock")
