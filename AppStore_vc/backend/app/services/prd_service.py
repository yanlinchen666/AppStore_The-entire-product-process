import json
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models import AnalysisRun, AnalysisFinding, PRDRequirement, PRDVersion
from app.utils.llm_client import llm_client

logger = logging.getLogger(__name__)

class PRDService:
    """
    NOTE on DB session lifecycle:
    MySQL's wait_timeout on this machine is 120s. Any SQLAlchemy session held
    idle across an LLM call (which can easily take 30-120+ seconds) will have
    its underlying connection closed by the server, and the next DB operation
    raises `mysql.connector.errors.OperationalError: MySQL Connection not available`.

    Therefore:
    - Methods that make LLM calls (`generate_requirements`, `plan_versions`)
      do NOT accept a `db` session parameter.
    - The top-level `generate_prd` method follows a strict 3-phase pattern:
        1. short DB session → read findings / versions (pure data)
        2. LLM calls (no DB session held)
        3. short DB session → persist results
    """
    def __init__(self):
        pass

    def get_findings_for_prd(self, db: Session, run_id: int) -> List[Dict]:
        findings = db.query(AnalysisFinding).filter(AnalysisFinding.run_id == run_id).all()
        results = []

        for finding in findings:
            results.append({
                'id': finding.id,
                'finding_text': finding.finding_text,
                'confidence': finding.confidence,
                'has_conflict': finding.has_conflict,
                'sample_count': finding.sample_count,
                'evidence_review_ids': finding.evidence_review_ids or [],
                'topic_id': finding.topic_id
            })

        return results

    def generate_requirements(self, findings: List[Dict]) -> List[Dict]:
        """Generate requirements via LLM. No DB session held here — LLM calls are slow."""
        findings_text = "\n".join([
            f"Finding {i+1} (Confidence: {f['confidence']:.2f}, Samples: {f['sample_count']}): {f['finding_text']}"
            for i, f in enumerate(findings)
        ])

        prompt = f"""
You are an expert product manager. Based on the following analysis findings, generate detailed product requirements for an update plan.

Analysis Findings ({len(findings)} total):
{findings_text}

Please provide a JSON array of requirements with the following structure:
[
    {{
        "requirement": "Clear, actionable requirement statement",
        "requirement_type": "feature" | "bug_fix" | "improvement" | "ui/ux" | "performance",
        "priority": "high" | "medium" | "low",
        "description": "Detailed description of what needs to be done",
        "user_value": "How this benefits users",
        "business_value": "How this benefits the business",
        "source_findings": [list_of_finding_ids_this_requirement_addresses],
        "estimated_effort": "low" | "medium" | "high",
        "version": "v1.0" | "v1.1" | "v2.0" (suggest which version this should go into)
    }}
]

Requirements:
1. Generate 5-10 requirements
2. Each requirement must directly address one or more findings
3. Prioritize based on user impact and business value
4. Split into logical versions
5. Ensure requirements are testable
6. Include both bug fixes and feature improvements
"""

        try:
            response = llm_client.chat_completion([{"role": "user", "content": prompt}])
            return self._parse_requirements_response(response)
        except Exception as e:
            logger.error(f"Requirement generation failed: {str(e)}")
            return self._fallback_requirements(findings)

    def _parse_requirements_response(self, response: str) -> List[Dict]:
        try:
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass
        return []

    def _fallback_requirements(self, findings: List[Dict]) -> List[Dict]:
        requirements = []
        
        for i, finding in enumerate(findings[:5]):
            requirements.append({
                "requirement": f"Address user feedback about: {finding['finding_text'][:50]}...",
                "requirement_type": "improvement",
                "priority": "high" if finding.get('confidence', 0) > 0.7 else "medium",
                "description": f"Based on user reviews, address the issue described in finding: {finding['finding_text']}",
                "user_value": "Improved user experience",
                "business_value": "Higher user satisfaction and retention",
                "source_findings": [finding['id']],
                "estimated_effort": "medium",
                "version": "v1.0"
            })
        
        return requirements

    def plan_versions(self, requirements: List[Dict]) -> List[Dict]:
        version_map = {}
        
        for req in requirements:
            version = req.get('version', 'v1.0')
            if version not in version_map:
                version_map[version] = {
                    'version_name': version,
                    'requirements': [],
                    'priority': 1 if version == 'v1.0' else 2,
                    'estimated_effort': "medium"
                }
            version_map[version]['requirements'].append(req)
        
        versions = []
        for version_name, data in version_map.items():
            versions.append({
                'version_name': version_name,
                'description': f"{len(data['requirements'])} requirements for this version",
                'priority': data['priority'],
                'estimated_effort': data['estimated_effort'],
                'requirements_count': len(data['requirements']),
                'requirements': data['requirements']
            })
        
        versions.sort(key=lambda x: x['priority'])
        return versions

    def save_prd(self, db: Session, run_id: int, requirements: List[Dict], versions: List[Dict]) -> None:
        for version_data in versions:
            version = PRDVersion(
                run_id=run_id,
                version_name=version_data['version_name'],
                description=version_data['description'],
                priority=version_data['priority'],
                estimated_effort=version_data['estimated_effort'],
                requirements_count=version_data['requirements_count']
            )
            db.add(version)
            db.flush()

        for req_data in requirements:
            source_findings = req_data.get('source_findings', [])
            finding_id = source_findings[0] if source_findings else None

            # Collect source review IDs from linked finding
            source_review_ids = []
            if finding_id:
                from app.models import AnalysisFinding
                linked_finding = db.query(AnalysisFinding).filter(AnalysisFinding.id == finding_id).first()
                if linked_finding and linked_finding.evidence_review_ids:
                    source_review_ids = linked_finding.evidence_review_ids

            requirement = PRDRequirement(
                run_id=run_id,
                finding_id=finding_id,
                requirement_text=req_data['requirement'],
                description=req_data.get('description', ''),
                user_value=req_data.get('user_value', ''),
                business_value=req_data.get('business_value', ''),
                requirement_type=req_data.get('requirement_type', 'improvement'),
                priority=req_data.get('priority', 'medium'),
                version=req_data.get('version', 'v1.0'),
                estimated_effort=req_data.get('estimated_effort', 'medium'),
                status="draft",
                source_review_ids=source_review_ids,
                is_model_generated=True
            )
            db.add(requirement)

        db.commit()
        logger.info(f"Saved {len(requirements)} requirements and {len(versions)} versions for run {run_id}")

    def generate_prd(self, db: Session, run_id: int) -> Dict[str, Any]:
        """
        Top-level PRD generation with strict session lifecycle:
        1. Short DB session to load findings (plain dicts).
        2. LLM generation (no DB session held).
        3. Short DB session to persist requirements and versions.
        We accept a `db` param for API compatibility with callers, but we
        do NOT hold it across the LLM call — we use it only for brief reads
        and then pass the data to pure-data generation methods.
        """
        findings = self.get_findings_for_prd(db, run_id)

        if len(findings) == 0:
            return {"status": "failed", "error": "No findings available for PRD generation"}

        # Phase 2: LLM generation — NO DB session held.
        requirements = self.generate_requirements(findings)
        versions = self.plan_versions(requirements)

        # Phase 3: short DB session to persist results.
        self.save_prd(db, run_id, requirements, versions)

        return {
            "status": "completed",
            "requirements_count": len(requirements),
            "versions_count": len(versions),
            "versions": versions
        }

prd_service = PRDService()