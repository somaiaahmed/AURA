from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel
from rich.console import Console
from rich.prompt import Prompt
from groq import Groq
import openai
from dotenv import load_dotenv
import os
import json
from pathlib import Path
from datetime import datetime


# Load environment variables
load_dotenv()

class RequirementType(Enum):
    BUSINESS = "business"
    STAKEHOLDER = "stakeholder"
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non-functional"

class Priority(Enum):
    MUST_HAVE = "Must Have"
    SHOULD_HAVE = "Should Have"
    COULD_HAVE = "Could Have"
    WONT_HAVE = "Won't Have"

class Requirement(BaseModel):
    id: str
    description: str
    type: RequirementType
    priority: Priority
    business_need: str
    source: str
    dependencies: List[str] = []
    status: str = "Draft"

class BusinessAnalystAgent:
    def __init__(self):
        self.console = Console()
        self.requirements: List[Requirement] = []
        self.conversation_history: List[Dict] = []
        self.requirement_counter = 1
        # self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Create output directory if it doesn't exist
        self.output_dir = "conversation_logs"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize completion flags for tracking interview progress
        self.completion_flags = {
            "business_context": False,
            "stakeholder_needs": False,
            "current_process": False,
            "desired_outcomes": False,
            "business_rules": False,
            "success_criteria": False,
            "time_cost_analysis": False
        }

    def start_interview(self):
        self.console.print("[bold green]Welcome! I'm your AI Business Analyst.[/bold green]")
        self.console.print("I'll help you gather and analyze requirements for your project.")
        self.console.print("Let's start with some basic questions about your business needs.")

        while True:
            user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
            
            # Break conditions
            if user_input.lower() in ['exit', 'quit', 'bye']:
                self.console.print("[bold yellow]Exiting the interview...[/bold yellow]")
                last_file = self._save_conversation(completed=True)
                if last_file:
                    self.last_saved_conversation = last_file
                    # Offer to export to JSON
                    export = Prompt.ask("Would you like to export the requirements to JSON? (y/n)", default="y")
                    if export.lower() == 'y':
                        json_file = Prompt.ask("Enter JSON filename", default="content.json")
                        self.save_requirements_to_json(json_file)
                break
                
            if all(self.completion_flags.values()):
                self.console.print("[bold green]All required data has been collected![/bold green]")
                confirm = Prompt.ask("Would you like to exit? (y/n)", default="y")
                if confirm.lower() == 'y':
                    self._show_summary()
                    last_file = self._save_conversation(completed=True)
                    if last_file:
                        self.last_saved_conversation = last_file
                        # Offer to export to JSON
                        export = Prompt.ask("Would you like to export the requirements to JSON? (y/n)", default="y")
                        if export.lower() == 'y':
                            json_file = Prompt.ask("Enter JSON filename", default="content.json")
                            self.save_requirements_to_json(json_file)
                    break
                

            # Process the input and generate response
            response = self._process_input(user_input)
            self.console.print(f"\n[bold green]Business Analyst:[/bold green] {response}")

    def _process_input(self, user_input: str) -> str:
        # Add user input to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})

        # Prepare the prompt for the AI
        system_prompt = """You are an experienced Business Analyst conducting a requirements gathering interview. Your role is to:

            1. Focus on business needs and goals
            2. Proactively suggest ideas and solutions based on user's needs
            3. Complete each topic thoroughly before moving to the next
            4. Listen carefully to the user's response
            5. Extract requirements as they are mentioned

            Follow this structured approach, completing each step fully before moving to the next:

            1. If this is the first interaction:
            - Ask about their business: "Could you tell me about your business and what you're trying to achieve?"

            2. Based on their previous answer, follow these topics in sequence, completing each fully before moving on:

            a. Business Context & Goals:
                - What is the main business problem you're trying to solve?
                - SUGGEST: "Based on similar businesses, you might want to consider measuring [specific metrics]"
                - SUGGEST: "Other companies in your industry often focus on [specific goals]"

            b. Stakeholder Needs:
                - Who are the main people involved in this process?
                - SUGGEST: "Have you considered how [specific stakeholder] might benefit from [specific improvement]?"
                - SUGGEST: "Other organizations have found success by [specific approach]"

            c. Current Process:
                - How do things work currently?
                - SUGGEST: "Based on your current process, you might benefit from [specific improvement]"
                - SUGGEST: "Other companies have improved similar processes by [specific solution]"

            d. Desired Outcomes:
                - What would help achieve your business goals?
                - SUGGEST: "You might want to consider [specific outcome] as it has helped similar businesses"
                - SUGGEST: "Based on your goals, [specific improvement] could be valuable"

            e. Business Rules & Requirements:
                - What are the must-follow rules or policies?
                - SUGGEST: "You might want to consider [specific policy] as it's common in your industry"
                - SUGGEST: "Other companies have found success with [specific approach]"

            f. Success Criteria:
                - How will you know if this is successful?
                - SUGGEST: "Based on your industry, these metrics are often important: [specific metrics]"
                - SUGGEST: "You might want to consider measuring [specific success criteria]"

            g. Time & Cost Analysis:

               - Time Management: "What is your ideal timeline for implementing the improvements we've discussed? Are there any critical deadlines or time constraints we should consider?"
               - Cost Constraints: "Do you have a specific budget allocated for this project, or any cost limitations that we should be mindful of during the solution design phase?"

               - SUGGEST: "Given the scope of the project, you may want to prioritize certain features to achieve a quicker return on investment. Other companies have often seen significant results by focusing on a phased implementation."

               - SUGGEST: "It might be worth exploring solutions that allow for incremental upgrades to avoid a large upfront cost while still improving the overall efficiency.
                
            Important Guidelines:
            - Focus on business needs, not technical solutions
            - Proactively suggest ideas and solutions based on user's needs
            - Ask ONE question at a time
            - Wait for user's complete response before moving to the next point
            - Always acknowledge their answer before asking the next question
            - Use phrases like "I understand that..." or "So, what you're saying is..."
            - If an answer is unclear, ask for clarification
            - Keep track of the current topic and ensure it's fully covered before moving on
            - Extract specific requirements as they are mentioned
            - Never discuss technical implementation details unless specifically asked
            - If user mentions technical solutions, redirect to business needs: "That's interesting. Could you tell me more about what business need that would address?"

            Remember: 
            - You are having a natural conversation
            - Focus on business value and outcomes
            - Complete each topic thoroughly before moving to the next
            - Keep the conversation business-focused
            - Extract requirements as they are mentioned
            - Be proactive in suggesting ideas and solutions
            - Use your experience to guide the conversation
            - Suggest improvements based on industry best practices"""

        try:
            # Get AI response
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *self.conversation_history
                ]
            )

            ai_response = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": ai_response})

            # Extract and store requirements if identified
            self._extract_requirements(ai_response)
            
            # Update completion flags
            self._update_completion_flags(ai_response, user_input)
            
            return ai_response
        except Exception as e:
            error_message = f"An error occurred while processing your request: {str(e)}"
            self.console.print(f"[bold red]{error_message}[/bold red]")
            return "I apologize, but I encountered an error. Please try again or rephrase your question."

    def _extract_requirements(self, text: str):
        # First try to use AI to identify requirements
        try:
            extraction_prompt = """Analyze the text below and identify any business requirements mentioned. 
            For each requirement found, extract:
            1. A clear description of the requirement
            2. The type (business, stakeholder, functional, non-functional)
            3. Priority level (Must Have, Should Have, Could Have, Won't Have)
            4. Business need it addresses
            
            Format each requirement on a new line prefixed with 'REQUIREMENT:' followed by the details in JSON format.
            If no requirements are found, respond with 'NO_REQUIREMENTS_FOUND'.
            
            Text to analyze:
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert business analyst who specializes in requirements extraction."},
                    {"role": "user", "content": extraction_prompt + text}
                ]
            )
            
            result = response.choices[0].message.content
            
            if "NO_REQUIREMENTS_FOUND" not in result:
                lines = result.split('\n')
                for line in lines:
                    if line.strip().startswith("REQUIREMENT:"):
                        req_data = line.replace("REQUIREMENT:", "").strip()
                        try:
                            # Try to parse as JSON
                            req_json = json.loads(req_data)
                            
                            # Map the type string to enum
                            type_map = {
                                "business": RequirementType.BUSINESS,
                                "stakeholder": RequirementType.STAKEHOLDER,
                                "functional": RequirementType.FUNCTIONAL,
                                "non-functional": RequirementType.NON_FUNCTIONAL
                            }
                            
                            # Map priority string to enum
                            priority_map = {
                                "must have": Priority.MUST_HAVE,
                                "should have": Priority.SHOULD_HAVE,
                                "could have": Priority.COULD_HAVE,
                                "won't have": Priority.WONT_HAVE
                            }
                            
                            req_type = type_map.get(req_json.get("type", "").lower(), RequirementType.BUSINESS)
                            req_priority = priority_map.get(req_json.get("priority", "").lower(), Priority.SHOULD_HAVE)
                            
                            req = Requirement(
                                id=f"REQ-{self.requirement_counter}",
                                description=req_json.get("description", ""),
                                type=req_type,
                                priority=req_priority,
                                business_need=req_json.get("business_need", "To be determined"),
                                source="Interview"
                            )
                            self.requirements.append(req)
                            self.requirement_counter += 1
                        except json.JSONDecodeError:
                            # Fallback to simple extraction if JSON fails
                            self._simple_requirement_extraction(line)
        except Exception as e:
            # Fallback to simple extraction on error
            self._simple_requirement_extraction(text)
    
    def _simple_requirement_extraction(self, text):
        """Simple requirement extraction as fallback"""
        if "requirement" in text.lower():
            req = Requirement(
                id=f"REQ-{self.requirement_counter}",
                description=text,
                type=RequirementType.BUSINESS,
                priority=Priority.MUST_HAVE,
                business_need="To be determined",
                source="Interview"
            )
            self.requirements.append(req)
            self.requirement_counter += 1

    def _update_completion_flags(self, ai_response, user_input):
        """Update completion flags based on conversation analysis"""
        # Combine user input and AI response for analysis
        combined_text = user_input + " " + ai_response
        
        # Check for topic indicators in the text
        if not self.completion_flags["business_context"] and any(term in combined_text.lower() for term in ["business problem", "business goal", "trying to achieve"]):
            self.completion_flags["business_context"] = True
            
        if not self.completion_flags["stakeholder_needs"] and any(term in combined_text.lower() for term in ["stakeholder", "people involved", "user needs"]):
            self.completion_flags["stakeholder_needs"] = True
            
        if not self.completion_flags["current_process"] and any(term in combined_text.lower() for term in ["current process", "how things work", "existing system"]):
            self.completion_flags["current_process"] = True
            
        if not self.completion_flags["desired_outcomes"] and any(term in combined_text.lower() for term in ["desired outcome", "goal", "objective", "what would help"]):
            self.completion_flags["desired_outcomes"] = True
            
        if not self.completion_flags["business_rules"] and any(term in combined_text.lower() for term in ["business rule", "policy", "regulation", "must-follow"]):
            self.completion_flags["business_rules"] = True
            
        if not self.completion_flags["success_criteria"] and any(term in combined_text.lower() for term in ["success criteria", "measure success", "metrics", "kpi"]):
            self.completion_flags["success_criteria"] = True
            
        if not self.completion_flags["time_cost_analysis"] and any(term in combined_text.lower() for term in ["timeline", "budget", "cost", "deadline", "time constraint"]):
            self.completion_flags["time_cost_analysis"] = True
    
    def _show_summary(self):
        """Display collected data before exiting"""
        self.console.print("\n[bold underline]SUMMARY OF COLLECTED DATA[/bold underline]")
        self.console.print(f"\n[bold]Topics Completed:[/bold] {sum(self.completion_flags.values())}/{len(self.completion_flags)}")
        self.console.print(f"[bold]Requirements Identified:[/bold] {len(self.requirements)}")
        
        if self.requirements:
            self.console.print("\n[bold]Requirements List:[/bold]")
            for req in self.requirements:
                self.console.print(f"- {req.id}: {req.description[:50]}...")

    def _save_conversation(self, completed: bool):
        """Save the entire conversation to a timestamped text file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/conversation_{timestamp}.txt"
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                # Write header
                f.write(f"Business Requirements Interview - {timestamp}\n")
                f.write(f"Status: {'COMPLETED' if completed else 'INCOMPLETE'}\n")
                f.write("-"*50 + "\n\n")
                
                # Write conversation history
                for msg in self.conversation_history:
                    role = "USER" if msg["role"] == "user" else "ANALYST"
                    f.write(f"{role}: {msg['content']}\n\n")
                
                # Write requirements summary
                if self.requirements:
                    f.write("\n\n" + "="*50 + "\n")
                    f.write("EXTRACTED REQUIREMENTS:\n")
                    for req in self.requirements:
                        f.write(f"\n{req.id} ({req.type.value}, {req.priority.value}):\n")
                        f.write(f"{req.description}\n")
                
                # Write completion status
                f.write("\n\n" + "="*50 + "\n")
                f.write("TOPIC COMPLETION STATUS:\n")
                for topic, status in self.completion_flags.items():
                    f.write(f"- {topic.replace('_', ' ').title()}: {'✔' if status else '✖'}\n")
            
            self.console.print(f"\n[bold green]Conversation saved to: {filename}[/bold green]")
            return filename
        except Exception as e:
            self.console.print(f"\n[bold red]Error saving conversation: {str(e)}[/bold red]")
            return None

    def save_requirements_to_json(self, output_file="content.json"):
        """Save extracted requirements and conversation insights to a structured JSON file"""
        # Create a professional business analysis document structure
        business_analysis = {
            "project_overview": {
                "title": "Requirements Analysis Document",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "status": "Draft"
            },
            "business_context": {
                "description": self._extract_topic_content("business_context"),
                "business_goals": self._extract_key_points("goals"),
                "pain_points": self._extract_key_points("problems")
            },
            "stakeholders": {
                "primary": self._extract_stakeholders(),
                "needs": self._extract_key_points("stakeholder needs")
            },
            "current_process": {
                "description": self._extract_topic_content("current_process"),
                "limitations": self._extract_key_points("limitations")
            },
            "requirements": {
                "functional": self._categorize_requirements(RequirementType.FUNCTIONAL),
                "non_functional": self._categorize_requirements(RequirementType.NON_FUNCTIONAL),
                "business": self._categorize_requirements(RequirementType.BUSINESS),
                "stakeholder": self._categorize_requirements(RequirementType.STAKEHOLDER)
            },
            "success_criteria": self._extract_key_points("success criteria"),
            "timeline_and_budget": {
                "estimated_timeline": self._extract_topic_content("timeline"),
                "budget_constraints": self._extract_topic_content("budget")
            },
            "recommendations": self._generate_recommendations(),
            "metadata": {
                "generated_by": "AI Business Analyst Agent",
                "generation_date": datetime.now().isoformat(),
                "conversation_file": Path(self.last_saved_conversation).name if hasattr(self, "last_saved_conversation") else None
            }
        }
        
        # Write to file
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(business_analysis, f, indent=2)
            self.console.print(f"\n[bold green]Business analysis saved to: {output_file}[/bold green]")
            return True
        except Exception as e:
            self.console.print(f"\n[bold red]Error saving business analysis: {str(e)}[/bold red]")
            return False

    def _extract_topic_content(self, topic):
        """Extract content related to a specific topic from conversation history"""
        # This uses AI to summarize conversation parts about a particular topic
        topic_prompt = f"Based on the conversation, provide a clear and concise summary of information about the {topic}. Format as a professional business analyst would."
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional business analyst. Summarize the following conversation content."},
                    *self.conversation_history,
                    {"role": "user", "content": topic_prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            self.console.print(f"[bold red]Error extracting {topic} content: {str(e)}[/bold red]")
            return f"Unable to extract {topic} information"

    def _extract_key_points(self, category):
        """Extract key points for a specific category from conversation history"""
        category_prompt = f"Based on the conversation, list the 3-5 most important {category} mentioned. Format each as a brief, clear statement a business analyst would write."
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional business analyst. Extract key points from this conversation."},
                    *self.conversation_history,
                    {"role": "user", "content": category_prompt}
                ]
            )
            
            # Extract bullet points from the response
            content = response.choices[0].message.content
            points = [line.strip().strip('*-•').strip() for line in content.split('\n') if line.strip() and not line.strip().lower().startswith(('here', 'the', 'key', 'important'))]
            return points[:5]  # Limit to 5 max
        except Exception as e:
            self.console.print(f"[bold red]Error extracting {category} points: {str(e)}[/bold red]")
            return []

    def _extract_stakeholders(self):
        """Extract stakeholders mentioned in the conversation"""
        stakeholder_prompt = "Based on the conversation, identify all stakeholders mentioned and their roles. Format as a list of stakeholders with brief descriptions."
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional business analyst. Identify stakeholders from this conversation."},
                    *self.conversation_history,
                    {"role": "user", "content": stakeholder_prompt}
                ]
            )
            
            content = response.choices[0].message.content
            # Process into a dictionary of stakeholder: role
            stakeholders = {}
            for line in content.split('\n'):
                if ':' in line:
                    parts = line.strip().split(':', 1)
                    stakeholders[parts[0].strip().strip('*-•')] = parts[1].strip()
                elif '-' in line:
                    parts = line.strip().split('-', 1)
                    stakeholders[parts[0].strip().strip('*•')] = parts[1].strip()
            return stakeholders
        except Exception as e:
            self.console.print(f"[bold red]Error extracting stakeholders: {str(e)}[/bold red]")
            return {}

    def _categorize_requirements(self, req_type):
        """Categorize and format requirements by type"""
        return [
            {
                "id": req.id,
                "description": req.description,
                "priority": req.priority.value,
                "business_need": req.business_need,
                "source": req.source,
                "dependencies": req.dependencies,
                "status": req.status
            }
            for req in self.requirements if req.type == req_type
        ]

    def _generate_recommendations(self):
        """Generate business recommendations based on the conversation"""
        recommendation_prompt = "Based on the entire conversation, provide 3-5 key recommendations that a professional business analyst would make to help this organization achieve their goals. Format as clear, actionable recommendations."
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional business analyst. Generate recommendations based on this conversation."},
                    *self.conversation_history,
                    {"role": "user", "content": recommendation_prompt}
                ]
            )
            
            content = response.choices[0].message.content
            recommendations = [line.strip().strip('*-•').strip() for line in content.split('\n') if line.strip() and not line.strip().lower().startswith(('here', 'the', 'recommendations', 'key'))]
            return recommendations
        except Exception as e:
            self.console.print(f"[bold red]Error generating recommendations: {str(e)}[/bold red]")
            return []


if __name__ == "__main__":
    agent = BusinessAnalystAgent()
    agent.start_interview()