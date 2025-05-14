import os
import openai
import ai_content.ai_config as ai_config

class CommentSmellAI:
    def __init__(self):
        """
        How to Use This Module
        from comment_smell_ai import CommentSmellAI
        ai_processor = CommentSmellAI()
        smell_label = ai_processor.detect_comment_smell(code_segment, comment_text)
        repair_suggestion = ai_processor.repair_comment(code_segment, comment_text, smell_label)
        """
        openai.api_base = ai_config.GPT_40_MINI_ENDPOINT
        openai.api_key = ai_config.GPT_40_MINI_API_KEY
        openai.api_version = "2024-12-01-preview"
        openai.api_type = "azure"
        self.deployment_id = ai_config.GPT_40_MINI_DEPLOYMENT
        if not self.deployment_id:
            raise ValueError("GPT_40_MINI_DEPLOYMENT is not set. Check your configuration.")

        # Taxonomy for classifying comment smells.
        self.taxonomy = """
Misleading: Comments that do not accurately represent what the code does.
Obvious: Comments that restate what the code does in an obvious manner.
Commented out code: Code that has been commented out.
Irrelevant: Comments that do not explain the code.
Task: TODO/FIXME comments that lack useful details.
Too much info: Overly verbose comments that hinder readability.
Beautification: Decorative comments with no functional meaning.
Nonlocal info: Comments referencing code far away.
Vague: Comments that lack clarity.
Not a smell: Comments that are clear, concise, and useful.
        """

    def get_chat_response(self, prompt, role="user", max_tokens=10):
        system_message = "Code comments should be clear, concise, and useful for maintainability."
        response = openai.ChatCompletion.create(
            deployment_id=self.deployment_id,
            messages=[
                {"role": "system", "content": system_message},
                {"role": role, "content": prompt}
            ],
            temperature=0.2,
            max_tokens=max_tokens
        )
        return response["choices"][0]["message"]["content"].strip()

    def detect_comment_smell(self, code, comment):
        """
        Detect the smell of a comment given a code segment and the comment text.

        Args:
            code (str): The associated code segment.
            comment (str): The comment text.
        
        Returns:
            A string representing the predicted smell category. The output is one of:
            [Misleading, Obvious, Commented out code, Irrelevant, Task, Too much info, Beautification, Nonlocal info, Vague, Not a smell].
        """
        prompt = f"""
You will be provided with a code segment and a corresponding inline code comment.
Using the following taxonomy:
{self.taxonomy}

Determine which category best describes the comment smell. If the comment does not exhibit a smell, label it as "Not a smell".
Do not provide any explanation; output exactly one label.

Code segment:
'''{code}'''

Comment:
'''{comment}'''
"""
        return self.get_chat_response(prompt, role="user")

    def repair_comment(self, code, comment, label, lang="java"):
        """
        Generate a repair suggestion for a given comment, informed by the detected smell label.

        Args:
            code (str): The associated code segment.
            comment (str): The original comment text.
            label (str): The detected smell label.

        Returns:
            A string containing the revised comment that is clear, concise, and accurate.
        """

        if(label == "Not a smell"):
            return comment
        elif label in ["Task", "Commented out code", "Beautification", "Obvious", "Attribution", "Irrelevant"]:
            return ""

        prompt = f"""
You are provided with a code segment, an inline code comment, and a label indicating the detected comment smell.
Using the label, rewrite the comment so that it is clear, concise, and accurately reflects what the code does.
Do not provide any explanation; output only the revised comment.

Label: {label}

Code segment:
'''{code}'''

Original comment:
'''{comment}'''
"""
        # Increase max_tokens as needed for repair suggestions.
        raw = self.get_chat_response(prompt, role="user", max_tokens=100)
        clean = raw.strip("`'\"")

        # 2) Remove one leading comment marker if present
        if lang.lower() == "java":
            # Drop any leading whitespace, then //, then any whitespace after
            tmp = clean.lstrip()
            if tmp.startswith("//"):
                clean = tmp[2:].lstrip()
        else:
            # Python: drop leading # 
            tmp = clean.lstrip()
            if tmp.startswith("#"):
                clean = tmp[1:].lstrip()

        # 3) Now `clean` has no leading `//` or `#`, nor backticks/quotes
        suggestion = clean

        return suggestion

