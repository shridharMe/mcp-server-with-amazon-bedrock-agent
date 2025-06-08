from typing import Any, Dict, List
import os
import json
import jenkins
import time
import requests
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("Jenkins MCP Server")

def get_jenkins_server():
    jenkins_url = os.getenv('JENKINS_URL', 'http://localhost:8080')
    username = "Shridhar"
    token = "**********"
    
    if not all([jenkins_url, username, token]):
        raise ValueError("Jenkins credentials not found in environment variables")
    
    return  jenkins.Jenkins(jenkins_url, username=username, password=token), username, token

@mcp.tool()
def get_pipeline_visualization(job_name: str, build_number: int) -> str:
    """
    Get pipeline visualization for a specific build with HTML formatting
    """
    try:
        server, username, token = get_jenkins_server()
        jenkins_url = os.getenv('JENKINS_URL', 'http://localhost:8080')
        
        # Get pipeline data using workflow API
        api_url = f"{jenkins_url}/job/{job_name}/{build_number}/wfapi/describe"
        response = requests.get(api_url, auth=(username, token))
        
        if response.status_code != 200:
            return f"Failed to get pipeline data. Status code: {response.status_code}"
            
        pipeline_data = response.json()
        stages = pipeline_data.get('stages', [])
        
        if not stages:
            return "No pipeline stages found in this build."
        
        # Generate visualization using markdown-style formatting
        visualization = f"# Pipeline Status for Build #{build_number}\n\n"
        
        for i, stage in enumerate(stages):
            # Get stage status symbol
            status_symbol = {
                'SUCCESS': '✅',
                'FAILURE': '❌',
                'IN_PROGRESS': '🔄',
                'RUNNING': '🔄',
                'SKIPPED': '⏭️',
                'ABORTED': '⛔',
                'UNKNOWN': '❓'
            }.get(stage['status'], '❓')
            
            # Format duration
            duration = stage.get('durationMillis', 0)
            duration_str = f"({duration/1000:.1f}s)" if duration > 0 else ""
            
            # Add stage with markdown formatting
            visualization += f"**{status_symbol} {stage['name']}** {duration_str}\n"
            
            # Add separator between stages
            if i < len(stages) - 1:
                visualization += "---\n"
        
        # Add summary with markdown formatting
        total_duration = pipeline_data.get('durationMillis', 0)
        successful_stages = sum(1 for stage in stages if stage['status'] == 'SUCCESS')
        
        visualization += "\n### Summary\n"
        visualization += f"* **Total Stages:** {len(stages)}\n"
        visualization += f"* **Successful Stages:** {successful_stages}\n"
        visualization += f"* **Total Duration:** {total_duration/1000:.1f}s\n"
        visualization += f"* **Status:** {pipeline_data.get('status', 'UNKNOWN')}\n"
        
        return visualization
        
    except Exception as e:
        return f"Error getting pipeline visualization: {str(e)}"

@mcp.tool()
def get_pipeline_status_table(job_name: str, build_number: int) -> str:
    """
    Get pipeline status as a formatted table
    """
    try:
        server, username, token = get_jenkins_server()
        jenkins_url = os.getenv('JENKINS_URL', 'http://localhost:8080')
        
        api_url = f"{jenkins_url}/job/{job_name}/{build_number}/wfapi/describe"
        response = requests.get(api_url, auth=(username, token))
        
        if response.status_code != 200:
            return f"Failed to get pipeline data. Status code: {response.status_code}"
            
        pipeline_data = response.json()
        stages = pipeline_data.get('stages', [])
        
        if not stages:
            return "No pipeline stages found in this build."
        
        # Create table header
        table = "| Stage | Status | Duration |\n"
        table += "|-------|--------|----------|\n"
        
        # Add rows for each stage
        for stage in stages:
            status_symbol = {
                'SUCCESS': '✅',
                'FAILURE': '❌',
                'IN_PROGRESS': '🔄',
                'RUNNING': '🔄',
                'SKIPPED': '⏭️',
                'ABORTED': '⛔',
                'UNKNOWN': '❓'
            }.get(stage['status'], '❓')
            
            duration = stage.get('durationMillis', 0)
            duration_str = f"{duration/1000:.1f}s"
            
            table += f"| {stage['name']} | {status_symbol} | {duration_str} |\n"
        
        # Add summary
        total_duration = pipeline_data.get('durationMillis', 0)
        table += f"\n**Build #{build_number} Summary:**\n"
        table += f"* Duration: {total_duration/1000:.1f}s\n"
        table += f"* Status: {pipeline_data.get('status', 'UNKNOWN')}\n"
        
        return table
        
    except Exception as e:
        return f"Error getting pipeline status: {str(e)}"

# @mcp.tool()
# def get_latest_build_visualization(job_name: str) -> str:
#     """
#     Get pipeline visualization for the latest build
    
#     Args:
#         job_name: Name of the Jenkins job
    
#     Returns:
#         String containing the pipeline visualization
#     """
#     try:
#         server = get_jenkins_server()
#         job_info = server.get_job_info(job_name)
        
#         if not job_info.get('lastBuild'):
#             return f"No builds found for job '{job_name}'"
            
#         latest_build = job_info['lastBuild']['number']
#         return get_pipeline_visualization(job_name, latest_build)
        
#     except Exception as e:
#         return f"Error getting latest build visualization: {str(e)}"

@mcp.tool()
def trigger_and_monitor_pipeline(job_name: str, parameters: str = None) -> str:
    """
    Trigger a Jenkins job and monitor its progress
    """
    try:
        server, _, _ = get_jenkins_server()
        params_dict = json.loads(parameters) if parameters else None
        
        # Trigger the job
        queue_id = server.build_job(job_name, parameters=params_dict)
        
        # Wait for job to start
        time.sleep(1)
        build_info = server.get_queue_item(queue_id)
        while 'executable' not in build_info:
            time.sleep(1)
            build_info = server.get_queue_item(queue_id)
        
        build_number = build_info['executable']['number']
        
        # Monitor the build
        while True:
            # Get both visualizations
            status_table = get_pipeline_status_table(job_name, build_number)
            pipeline_vis = get_pipeline_visualization(job_name, build_number)
            
            # Combine them
            combined_output = f"{status_table}\n\n{pipeline_vis}"
            
            # Check if build is complete
            build_info = server.get_build_info(job_name, build_number)
            if not build_info['building']:
                return combined_output
            
            time.sleep(5)
            
    except Exception as e:
        return f"Error monitoring pipeline: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
