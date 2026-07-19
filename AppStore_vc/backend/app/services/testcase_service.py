import json
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models import PRDRequirement, TestCase, AnalysisFinding, Review
from app.utils.llm_client import llm_client

logger = logging.getLogger(__name__)

class TestCaseService:
    def __init__(self):
        pass

    def get_requirements(self, db: Session, run_id: int) -> List[Dict]:
        requirements = db.query(PRDRequirement).filter(PRDRequirement.run_id == run_id).all()
        results = []
        
        for req in requirements:
            finding = None
            if req.finding_id:
                finding = db.query(AnalysisFinding).filter(AnalysisFinding.id == req.finding_id).first()
            
            results.append({
                'id': req.id,
                'requirement_text': req.requirement_text,
                'requirement_type': req.requirement_type,
                'priority': req.priority,
                'version': req.version,
                'description': req.description if hasattr(req, 'description') else '',
                'finding_text': finding.finding_text if finding else ''
            })
        
        return results

    def generate_test_cases(self, db: Session, run_id: int, requirements: List[Dict]) -> List[Dict]:
        requirements_text = "\n".join([
            f"Requirement {i+1} (Type: {r['requirement_type']}, Priority: {r['priority']}, Version: {r['version']}): {r['requirement_text']}"
            for i, r in enumerate(requirements)
        ])

        prompt = f"""
You are an expert QA engineer. Based on the following product requirements, generate comprehensive test cases.

Product Requirements ({len(requirements)} total):
{requirements_text}

Please provide a JSON array of test cases with the following structure:
[
    {{
        "requirement_id": id_of_requirement_this_tests,
        "case_title": "Clear test case title",
        "case_description": "Detailed description of what this test verifies",
        "test_steps": ["Step 1", "Step 2", "Step 3"],
        "expected_result": "What should happen when the test passes",
        "test_type": "functional" | "ui" | "performance" | "regression" | "usability",
        "priority": "high" | "medium" | "low",
        "preconditions": ["What needs to be set up before the test"],
        "postconditions": ["What happens after the test"]
    }}
]

Requirements:
1. Generate 2-4 test cases per requirement
2. Each test case must be traceable to a specific requirement
3. Include both positive and negative test scenarios
4. Ensure test cases are actionable and verifiable
5. Include preconditions and postconditions
6. Cover edge cases
"""

        try:
            response = llm_client.chat_completion([{"role": "user", "content": prompt}])
            return self._parse_test_cases_response(response)
        except Exception as e:
            logger.error(f"Test case generation failed: {str(e)}")
            return self._fallback_test_cases(requirements)

    def _parse_test_cases_response(self, response: str) -> List[Dict]:
        try:
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass
        return []

    def _fallback_test_cases(self, requirements: List[Dict]) -> List[Dict]:
        test_cases = []
        
        for req in requirements:
            test_cases.append({
                "requirement_id": req['id'],
                "case_title": f"Test: {req['requirement_text'][:30]}...",
                "case_description": f"Verify that the requirement '{req['requirement_text']}' works correctly",
                "test_steps": ["Navigate to the relevant feature", "Perform the action", "Verify the result"],
                "expected_result": "The feature should work as expected",
                "test_type": "functional",
                "priority": req.get('priority', 'medium'),
                "preconditions": ["App is installed and running"],
                "postconditions": ["Feature works correctly"]
            })
        
        return test_cases

    def save_test_cases(self, db: Session, run_id: int, test_cases: List[Dict]) -> None:
        for tc_data in test_cases:
            test_case = TestCase(
                requirement_id=tc_data.get('requirement_id'),
                run_id=run_id,
                case_title=tc_data['case_title'],
                case_description=tc_data.get('case_description', ''),
                test_steps=tc_data.get('test_steps', []),
                expected_result=tc_data['expected_result'],
                test_type=tc_data.get('test_type', 'functional'),
                priority=tc_data.get('priority', 'medium'),
                source_review_ids=[],
                is_model_generated=True
            )
            db.add(test_case)
        
        db.commit()
        logger.info(f"Saved {len(test_cases)} test cases for run {run_id}")

    def generate_test_cases_for_prd(self, db: Session, run_id: int) -> Dict[str, Any]:
        requirements = self.get_requirements(db, run_id)
        
        if len(requirements) == 0:
            return {"status": "failed", "error": "No requirements available for test case generation"}
        
        test_cases = self.generate_test_cases(db, run_id, requirements)
        
        self.save_test_cases(db, run_id, test_cases)
        
        return {
            "status": "completed",
            "test_cases_count": len(test_cases),
            "requirements_count": len(requirements)
        }

testcase_service = TestCaseService()