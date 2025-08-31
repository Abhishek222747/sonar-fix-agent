"""
Hybrid Sonar Issue Fixer

Combines AST analysis, semantic analysis, and LLM capabilities to fix SonarQube issues.
"""
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import os
import openai

from .java_ast import JavaASTAnalyzer
from .java_semantic_analyzer import SemanticAnalyzer

@dataclass
class SonarIssue:
    rule: str
    message: str
    file_path: str
    line: int
    context: Dict[str, Any] = field(default_factory=dict)

class HybridSonarFixer:
    """Fixes SonarQube issues using a hybrid approach."""
    
    def __init__(self, project_root: str, openai_api_key: str = None):
        self.project_root = Path(project_root).resolve()
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.ast_cache: Dict[str, JavaASTAnalyzer] = {}
        self.semantic_cache: Dict[str, SemanticAnalyzer] = {}
        
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
    
    def fix_issues(self, issues: List[SonarIssue]) -> Dict[str, Any]:
        """Fix a list of SonarQube issues."""
        results = {"fixed": [], "failed": []}
        
        for issue in issues:
            try:
                fix_result = self._fix_issue(issue)
                if fix_result.get("success"):
                    results["fixed"].append(fix_result)
                else:
                    results["failed"].append(fix_result)
            except Exception as e:
                results["failed"].append({
                    "file": issue.file_path,
                    "line": issue.line,
                    "rule": issue.rule,
                    "error": str(e)
                })
        
        return results
    
    def _fix_issue(self, issue: SonarIssue) -> Dict[str, Any]:
        """Fix a single issue using the best available approach."""
        file_path = self.project_root / issue.file_path
        
        # Get analyzers
        ast_analyzer = self._get_ast_analyzer(file_path)
        semantic_analyzer = self._get_semantic_analyzer(file_path, ast_analyzer)
        
        # Try AST-based fix first
        ast_fix = self._try_ast_fix(issue, ast_analyzer)
        if ast_fix.get("success"):
            return ast_fix
            
        # Try semantic fix
        semantic_fix = self._try_semantic_fix(issue, semantic_analyzer)
        if semantic_fix.get("success"):
            return semantic_fix
            
        # Fall back to LLM if available
        if self.openai_api_key:
            llm_fix = self._try_llm_fix(issue, ast_analyzer, semantic_analyzer)
            if llm_fix.get("success"):
                return llm_fix
        
        return {
            "success": False,
            "file": issue.file_path,
            "line": issue.line,
            "rule": issue.rule,
            "reason": "No fixer available for this issue"
        }
    
    def _get_ast_analyzer(self, file_path: Path) -> JavaASTAnalyzer:
        """Get or create an AST analyzer for the file."""
        if str(file_path) not in self.ast_cache:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.ast_cache[str(file_path)] = JavaASTAnalyzer(f.read(), str(file_path))
        return self.ast_cache[str(file_path)]
    
    def _get_semantic_analyzer(self, file_path: Path, 
                             ast_analyzer: JavaASTAnalyzer) -> SemanticAnalyzer:
        """Get or create a semantic analyzer for the file."""
        if str(file_path) not in self.semantic_cache:
            self.semantic_cache[str(file_path)] = SemanticAnalyzer(ast_analyzer)
        return self.semantic_cache[str(file_path)]
    
    def _try_ast_fix(self, issue: SonarIssue, 
                    ast_analyzer: JavaASTAnalyzer) -> Dict[str, Any]:
        """Try to fix using AST transformations."""
        # Implementation would go here
        return {"success": False, "reason": "AST fix not implemented"}
    
    def _try_semantic_fix(self, issue: SonarIssue,
                         semantic_analyzer: SemanticAnalyzer) -> Dict[str, Any]:
        """Try to fix using semantic analysis."""
        # Implementation would go here
        return {"success": False, "reason": "Semantic fix not implemented"}
    
    def _try_llm_fix(self, issue: SonarIssue,
                    ast_analyzer: JavaASTAnalyzer,
                    semantic_analyzer: SemanticAnalyzer) -> Dict[str, Any]:
        """Try to fix using LLM."""
        try:
            # Get context
            context = self._get_llm_context(issue, ast_analyzer, semantic_analyzer)
            
            # Call LLM
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": "You are a Java expert fixing SonarQube issues."},
                         {"role": "user", "content": self._build_llm_prompt(issue, context)}],
                temperature=0.2,
                max_tokens=1000
            )
            
            return {
                "success": True,
                "fix": response.choices[0].message.content.strip(),
                "fix_type": "llm"
            }
            
        except Exception as e:
            return {
                "success": False,
                "reason": f"LLM fix failed: {str(e)}"
            }
    
    def _get_llm_context(self, issue: SonarIssue,
                        ast_analyzer: JavaASTAnalyzer,
                        semantic_analyzer: SemanticAnalyzer) -> Dict[str, Any]:
        """Get context for LLM."""
        return {
            "file": issue.file_path,
            "rule": issue.rule,
            "message": issue.message,
            "line": issue.line,
            "imports": list(getattr(ast_analyzer, 'imports', []))
        }
    
    def _build_llm_prompt(self, issue: SonarIssue, 
                         context: Dict[str, Any]) -> str:
        """Build prompt for LLM."""
        return f"""Fix this SonarQube issue:
Rule: {issue.rule}
Message: {issue.message}
File: {issue.file_path}
Line: {issue.line}

Provide only the fixed code."""
