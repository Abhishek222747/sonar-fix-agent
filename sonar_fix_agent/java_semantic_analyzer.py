"""
Semantic Analyzer for Java Code

This module provides semantic analysis capabilities for Java code, building on top of the AST analysis.
It includes type checking, variable usage analysis, and other semantic validations.
"""
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import javalang

from .java_ast import JavaASTAnalyzer, VariableInfo, MethodCallInfo, JavaMethod, JavaClass


@dataclass
class TypeInfo:
    """Represents type information for semantic analysis."""
    name: str
    is_primitive: bool = False
    is_array: bool = False
    element_type: Optional['TypeInfo'] = None
    type_parameters: List['TypeInfo'] = field(default_factory=list)
    
    def __str__(self) -> str:
        if self.is_array and self.element_type:
            return f"{self.element_type}[]"
        if self.type_parameters:
            params = ", ".join(str(p) for p in self.type_parameters)
            return f"{self.name}<{params}>"
        return self.name


@dataclass
class SymbolTable:
    """Manages symbols (variables, methods, types) in different scopes."""
    scopes: List[Dict[str, Any]] = field(default_factory=lambda: [{}])
    
    def enter_scope(self) -> None:
        """Enter a new scope."""
        self.scopes.append({})
    
    def exit_scope(self) -> None:
        """Exit the current scope."""
        if len(self.scopes) > 1:  # Keep the global scope
            self.scopes.pop()
    
    def add_symbol(self, name: str, symbol: Any) -> None:
        """Add a symbol to the current scope."""
        if self.scopes:
            self.scopes[-1][name] = symbol
    
    def lookup(self, name: str) -> Optional[Any]:
        """Look up a symbol in the current and enclosing scopes."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None


class SemanticAnalyzer:
    """Performs semantic analysis on Java code."""
    
    def __init__(self, ast_analyzer: JavaASTAnalyzer):
        """Initialize with an existing AST analyzer."""
        self.ast_analyzer = ast_analyzer
        self.symbol_table = SymbolTable()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.current_class: Optional[JavaClass] = None
        self.current_method: Optional[JavaMethod] = None
        self.type_registry: Dict[str, TypeInfo] = self._initialize_type_registry()
    
    def analyze(self) -> Dict[str, Any]:
        """
        Perform semantic analysis on the code.
        
        Returns:
            Dict containing analysis results including errors, warnings, and semantic information.
        """
        try:
            # Process all classes and their members
            for class_name, java_class in self.ast_analyzer.classes.items():
                self._process_class(java_class)
            
            return {
                'errors': self.errors,
                'warnings': self.warnings,
                'symbol_table': self._get_symbol_table_summary(),
                'type_info': self._get_type_info_summary()
            }
            
        except Exception as e:
            error_msg = f"Semantic analysis failed: {str(e)}"
            self.errors.append(error_msg)
            import traceback
            traceback.print_exc()
            return {'errors': [error_msg], 'warnings': self.warnings}
    
    def _initialize_type_registry(self) -> Dict[str, TypeInfo]:
        """Initialize the type registry with built-in Java types."""
        primitive_types = [
            'boolean', 'byte', 'char', 'short', 'int', 'long', 'float', 'double', 'void'
        ]
        
        common_types = [
            'Object', 'String', 'Number', 'Integer', 'Long', 'Double', 'Float',
            'Boolean', 'Character', 'Byte', 'Short', 'Void', 'Exception',
            'RuntimeException', 'Iterable', 'Collection', 'List', 'ArrayList',
            'Set', 'HashSet', 'Map', 'HashMap', 'Optional'
        ]
        
        type_registry = {}
        
        # Add primitive types
        for t in primitive_types:
            type_registry[t] = TypeInfo(name=t, is_primitive=True)
        
        # Add common reference types (java.lang)
        for t in common_types:
            full_name = f"java.lang.{t}" if t not in primitive_types else t
            type_registry[t] = TypeInfo(name=full_name)
        
        return type_registry
    
    def _process_class(self, java_class: JavaClass) -> None:
        """Process a class and its members for semantic analysis."""
        self.current_class = java_class
        self.symbol_table.enter_scope()
        
        try:
            # Add class fields to symbol table
            for field_name, field_type in java_class.fields.items():
                if field_name in java_class.field_info:
                    var_info = java_class.field_info[field_name]
                    self.symbol_table.add_symbol(field_name, var_info)
            
            # Process methods
            for method_name, method in java_class.methods.items():
                self._process_method(method)
                
        finally:
            self.symbol_table.exit_scope()
            self.current_class = None
    
    def _process_method(self, method: JavaMethod) -> None:
        """Process a method for semantic analysis."""
        self.current_method = method
        self.symbol_table.enter_scope()
        
        try:
            # Add parameters to symbol table
            for param_name, param_type in zip(method.parameter_names, method.parameter_types):
                var_info = VariableInfo(
                    name=param_name,
                    type_name=param_type,
                    is_parameter=True,
                    is_used=True,
                    declaration_line=method.start_line
                )
                self.symbol_table.add_symbol(param_name, var_info)
            
            # Analyze method body for variable usage
            self._analyze_variable_usage(method)
            
            # Check for unused parameters
            self._check_unused_parameters(method)
            
        finally:
            self.symbol_table.exit_scope()
            self.current_method = None
    
    def _analyze_variable_usage(self, method: JavaMethod) -> None:
        """Analyze variable usage within a method."""
        # This is a simplified version - in a real implementation, we would traverse the AST
        # to track variable usages, assignments, etc.
        
        # Mark all variables as unused initially
        for var_name, var_info in method.variables.items():
            var_info.is_used = False
        
        # Simple analysis: if a variable appears in any method call, consider it used
        for call in method.method_calls:
            # Check if any variable is used as an argument
            for arg in call.arguments:
                # This is a simplification - in reality, we'd need to parse the argument
                # expression to see which variables it references
                for var_name in method.variables:
                    if f"{var_name} " in arg or f" {var_name}" in arg:
                        method.variables[var_name].is_used = True
    
    def _check_unused_parameters(self, method: JavaMethod) -> None:
        """Check for unused method parameters."""
        for param_name in method.parameter_names:
            var_info = method.get_variable(param_name)
            if var_info and not var_info.is_used and param_name != "_":
                self.warnings.append(
                    f"Unused parameter '{param_name}' in method '{method.name}' at line {method.start_line}"
                )
    
    def find_unused_variables(self) -> List[VariableInfo]:
        """Find unused variables in the analyzed code."""
        unused_vars = []
        
        for java_class in self.ast_analyzer.classes.values():
            # Check fields
            for field_name, var_info in java_class.field_info.items():
                if not var_info.is_used and not var_info.name.startswith('_'):
                    unused_vars.append(var_info)
            
            # Check method variables
            for method in java_class.methods.values():
                for var_name, var_info in method.variables.items():
                    if not var_info.is_used and not var_info.is_parameter and not var_name.startswith('_'):
                        unused_vars.append(var_info)
        
        return unused_vars
    
    def find_unused_imports(self) -> List[str]:
        """Find unused imports in the analyzed code."""
        # This is a simplified check - a real implementation would track usage of imported types
        # and report any that are imported but never used.
        return []
    
    def _get_symbol_table_summary(self) -> Dict[str, Any]:
        """Get a summary of the symbol table for reporting."""
        summary = {
            'classes': {},
            'methods': {},
            'variables': {}
        }
        
        for class_name, java_class in self.ast_analyzer.classes.items():
            summary['classes'][class_name] = {
                'fields': list(java_class.fields.keys()),
                'methods': list(java_class.methods.keys())
            }
            
            for method_name, method in java_class.methods.items():
                full_method_name = f"{class_name}.{method_name}"
                summary['methods'][full_method_name] = {
                    'parameters': method.parameters,
                    'return_type': method.return_type,
                    'variables': list(method.variables.keys())
                }
        
        return summary
    
    def _get_type_info_summary(self) -> Dict[str, Any]:
        """Get a summary of type information for reporting."""
        return {
            'registered_types': list(self.type_registry.keys())
        }
