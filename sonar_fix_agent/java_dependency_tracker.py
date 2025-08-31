"""
Dependency Tracker for Java Projects

This module tracks dependencies between Java files to enable cross-file analysis.
"""
import os
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
import re
from .java_ast import JavaASTAnalyzer, JavaClass, JavaMethod


@dataclass
class JavaFileDependencies:
    """Stores dependency information for a single Java file."""
    file_path: str
    package: str
    imports: Set[str] = field(default_factory=set)
    classes: Set[str] = field(default_factory=set)
    depends_on: Set[str] = field(default_factory=set)  # Other files this file depends on
    used_by: Set[str] = field(default_factory=set)     # Other files that depend on this file
    

class JavaDependencyTracker:
    """Tracks dependencies between Java files in a project."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.files: Dict[str, JavaFileDependencies] = {}
        self.class_map: Dict[str, str] = {}  # Maps fully qualified class names to file paths
        
    def analyze_project(self) -> None:
        """Analyze all Java files in the project and build the dependency graph."""
        # First pass: collect all files and their basic information
        self._collect_file_metadata()
        
        # Second pass: resolve dependencies
        self._resolve_dependencies()
    
    def _collect_file_metadata(self) -> None:
        """Collect metadata from all Java files in the project."""
        for java_file in self.project_root.rglob('*.java'):
            try:
                analyzer = JavaASTAnalyzer(java_file.read_text(encoding='utf-8'), str(java_file))
                analysis = analyzer.analyze()
                
                # Create file dependencies entry
                rel_path = str(java_file.relative_to(self.project_root))
                file_deps = JavaFileDependencies(
                    file_path=rel_path,
                    package=analysis['package'] or '',
                    imports=set(analysis['imports'])
                )
                
                # Track classes defined in this file
                for class_name in analysis['classes']:
                    file_deps.classes.add(class_name)
                    self.class_map[class_name] = rel_path
                
                self.files[rel_path] = file_deps
                
            except Exception as e:
                print(f"Error analyzing {java_file}: {str(e)}")
    
    def _resolve_dependencies(self) -> None:
        """Resolve dependencies between files based on imports and class usage."""
        for file_path, file_deps in self.files.items():
            # Dependencies from imports
            for imp in file_deps.imports:
                # Convert import to class name
                if imp.endswith('.*'):
                    # Handle wildcard imports (simplified)
                    package = imp[:-2]
                    for class_name, class_file in self.class_map.items():
                        if class_name.startswith(package):
                            if class_file != file_path:  # Don't add self as dependency
                                file_deps.depends_on.add(class_file)
                                self.files[class_file].used_by.add(file_path)
                else:
                    # Handle specific class imports
                    if imp in self.class_map and self.class_map[imp] != file_path:
                        file_deps.depends_on.add(self.class_map[imp])
                        self.files[self.class_map[imp]].used_by.add(file_path)
    
    def get_dependent_files(self, file_path: str) -> Set[str]:
        """Get all files that depend on the specified file."""
        if file_path in self.files:
            return self.files[file_path].used_by
        return set()
    
    def get_file_dependencies(self, file_path: str) -> Set[str]:
        """Get all files that the specified file depends on."""
        if file_path in self.files:
            return self.files[file_path].depends_on
        return set()
    
    def find_class_file(self, class_name: str) -> Optional[str]:
        """Find the file containing the specified class."""
        return self.class_map.get(class_name)
    
    def get_impact_analysis(self, file_path: str) -> Dict[str, Set[str]]:
        """
        Perform impact analysis for changes to a file.
        
        Returns:
            Dict with 'direct' and 'transitive' sets of affected files
        """
        if file_path not in self.files:
            return {'direct': set(), 'transitive': set()}
            
        # Direct dependents (files that directly depend on this file)
        direct = set(self.files[file_path].used_by)
        
        # Transitive dependents (files that depend on the direct dependents, etc.)
        transitive = set()
        visited = set()
        
        def visit(dependent):
            if dependent in visited:
                return
            visited.add(dependent)
            
            if dependent in self.files:
                for user in self.files[dependent].used_by:
                    if user != file_path:  # Avoid cycles
                        transitive.add(user)
                        visit(user)
        
        for dep in direct:
            visit(dep)
            
        return {
            'direct': direct,
            'transitive': transitive - direct  # Only include indirect dependents
        }
