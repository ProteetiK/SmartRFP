"""
Prompt Builder for SmartRFP

Responsibilities
----------------
1. Build prompts for RAG
2. Inject retrieved context
3. Keep prompts reusable
4. Support proposal generation
"""


class PromptBuilder:

    @staticmethod
    def build_rag_prompt(
        query: str,
        context: str,
    ) -> str:
        """
        Build prompt using retrieved context.
        """

        return f"""
You are an expert RFP Proposal Assistant.

Your responsibility is to answer ONLY using the provided context.

If the answer cannot be found inside the context,
respond with:

"I could not find this information in the uploaded RFP."

Do NOT hallucinate.

----------------------------------------
Retrieved Context
----------------------------------------

{context}

----------------------------------------
User Question
----------------------------------------

{query}

----------------------------------------
Answer
----------------------------------------
"""

    @staticmethod
    def build_proposal_prompt(
        rfp_text: str,
        retrieved_context: str,
    ) -> str:
        """
        Generate proposal draft.
        """

        return f"""
You are a Senior Proposal Manager.

Use both the uploaded RFP and retrieved knowledge
to generate a professional proposal.

Requirements

1. Executive Summary
2. Scope
3. Deliverables
4. Timeline
5. Assumptions
6. Risks
7. Pricing Considerations

Uploaded RFP

{rfp_text}

Relevant Knowledge

{retrieved_context}

Generate a professional proposal.
"""

    @staticmethod
    def build_requirement_extraction_prompt(
        context: str,
    ) -> str:

        return f"""
You are an RFP Requirement Extraction Expert.

Extract all requirements.

Return JSON.

Context

{context}
"""

    @staticmethod
    def build_pricing_prompt(
        context: str,
    ) -> str:

        return f"""
You are a Cost Estimation Expert.

Estimate:

- Resources
- Timeline
- Team Size
- Cost Drivers

Context

{context}
"""

    @staticmethod
    def build_compliance_prompt(
        context: str,
    ) -> str:

        return f"""
You are a Compliance Auditor.

Check whether the proposal satisfies all requirements.

Context

{context}
"""