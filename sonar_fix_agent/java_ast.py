"""
Java AST Analyzer for Sonar Fix Agent

This module provides AST-based analysis for Java code to enable complex Sonar issue fixes.
"""
import os
import re
import javalang
import ast
import os
from typing import Dict, List, Set, Optional, Tuple, Any, Union, cast
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict


@dataclass
class VariableInfo:
    """Represents a variable in the code with its type and usage information."""
    name: str
    type_name: str
    is_field: bool = False
    is_parameter: bool = False
    is_used: bool = True
    is_modified: bool = False
    declaration_line: int = -1
    usage_lines: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'type': self.type_name,
            'is_field': self.is_field,
            'is_parameter': self.is_parameter,
            'is_used': self.is_used,
            'is_modified': self.is_modified,
            'declaration_line': self.declaration_line,
            'usage_lines': self.usage_lines
        }

@dataclass
class MethodCallInfo:
    """Represents a method call in the code."""
    method_name: str
    receiver_type: str
    arguments: List[str]
    line: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'method_name': self.method_name,
            'receiver_type': self.receiver_type,
            'arguments': self.arguments,
            'line': self.line
        }

@dataclass
class JavaMethod:
    name: str
    parameters: List[str]  # Full parameter strings (e.g., "String name")
    parameter_names: List[str]  # Just the parameter names
    parameter_types: List[str]  # Just the parameter types
    return_type: str
    modifiers: List[str]
    start_line: int
    end_line: int
    variables: Dict[str, VariableInfo] = field(default_factory=dict)
    method_calls: List[MethodCallInfo] = field(default_factory=list)
    
    def get_variable(self, name: str) -> Optional[VariableInfo]:
        """Get variable by name, checking parameters first."""
        if name in self.variables:
            return self.variables[name]
        if name in self.parameter_names:
            idx = self.parameter_names.index(name)
            return VariableInfo(
                name=name,
                type_name=self.parameter_types[idx],
                is_parameter=True
            )
        return None
    

@dataclass
class JavaClass:
    name: str
    package: str
    is_interface: bool
    is_abstract: bool
    methods: Dict[str, JavaMethod] = field(default_factory=dict)
    fields: Dict[str, str] = field(default_factory=dict)
    field_info: Dict[str, VariableInfo] = field(default_factory=dict)
    parent_class: Optional[str] = None
    interfaces: List[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0


class JavaASTAnalyzer:
    """
    Enhanced Java source code analyzer with semantic analysis capabilities.
    
    Features:
    - AST parsing with javalang
    - Semantic analysis (variable scopes, types, usages)
    - Cross-reference tracking
    - Support for incremental updates
    """
    
    def __init__(self, source_code: str, file_path: Optional[Union[str, Path]] = None):
        self.source_code = source_code
        self.file_path = str(file_path) if file_path else None
        self.lines = source_code.split('\n')
        self.tree = None
        self.classes: Dict[str, JavaClass] = {}
        self.imports: Dict[str, str] = {}  # simple_name -> full_import
        self.imported_classes: Dict[str, str] = {}  # simple_name -> full_import
        self.package = ""
        
        # Semantic analysis state
        self._current_class: Optional[JavaClass] = None
        self._current_method: Optional[JavaMethod] = None
        self._variable_scopes: List[Dict[str, VariableInfo]] = [{}]
        self._type_resolver: Dict[str, str] = {}  # simple_name -> full_name
        self._method_calls: List[MethodCallInfo] = []
        self._imported_star: bool = False  # Track if there's a wildcard import
        
    def analyze(self) -> None:
        """
        Perform the actual AST parsing and analysis.
        This is separated from __init__ to allow for lazy loading.
        """
        if self.tree is not None:
            return
            
        try:
            # First try full parsing
            self.tree = javalang.parse.parse(self.source_code)
            self._extract_package_and_imports()
            
            # Process all type declarations (classes, interfaces, enums)
            # Add error handling for ReferenceType issues
            if hasattr(self.tree, 'types') and self.tree.types:
                for type_decl in self.tree.types:
                    try:
                        if hasattr(type_decl, 'name') and type_decl.name:
                            self._process_type_declaration(type_decl)
                    except Exception as e:
                        print(f"[AST] Warning: Error processing type declaration: {e}")
                        continue
            for type_decl in self.tree.types:
                try:
                    if isinstance(type_decl, javalang.tree.ClassDeclaration):
                        self._process_class(type_decl)
                    elif isinstance(type_decl, javalang.tree.InterfaceDeclaration):
                        self._process_interface(type_decl)
                except Exception as e:
                    print(f"[AST] Warning: Error processing type declaration: {str(e)}")
                    continue
            
            if self.package:
                for class_name in self.classes.keys():
                    try:
                        simple_name = class_name.split('.')[-1]
                        self._type_resolver[simple_name] = class_name
                    except Exception as e:
                        print(f"[AST] Warning: Error processing class {class_name}: {str(e)}")
                        continue
                        
        except javalang.parser.JavaSyntaxError as e:
            print(f"[AST] Syntax error in {self.file_path or 'source'}: {e}")
            # Fall back to a minimal working tree
            self.tree = type('SimpleTree', (), {'types': []})()
        except Exception as e:
            print(f"[AST] Error analyzing {self.file_path or 'source'}: {str(e)}")
            self.tree = type('SimpleTree', (), {'types': []})()
    
    def _process_class(self, class_node: javalang.tree.ClassDeclaration) -> None:
        """Process a class declaration with full semantic information."""
        class_name = class_node.name
        full_name = f"{self.package}.{class_name}" if self.package else class_name
        
        # Create class metadata with detailed information
        java_class = JavaClass(
            name=class_name,
            package=self.package,
            is_interface=False,
            is_abstract='abstract' in [m.lower() for m in class_node.modifiers or []]
        )
        
        # Store current class for semantic analysis
        prev_class = self._current_class
        self._current_class = java_class
        
        try:
            # Process class-level annotations
            for annotation in class_node.annotations:
                # Extract annotation details if needed
                pass
            
            # Process fields with type information
            for field in class_node.fields:
                field_type = self._resolve_type(field.type)
                field_modifiers = [m.lower() for m in (field.modifiers or [])]
                
                for declarator in field.declarators:
                    var_info = VariableInfo(
                        name=declarator.name,
                        type_name=field_type,
                        is_field=True,
                        is_used=False,  # Will be updated during semantic analysis
                        is_modified=False,
                        declaration_line=field.position.line if field.position else -1
                    )
                    java_class.fields[declarator.name] = field_type
                    java_class.field_info[declarator.name] = var_info
            
            # Process methods
            for method in class_node.methods:
                self._process_method(method, java_class)
            
            # Process inner classes
            for inner_type in class_node.body:
                if isinstance(inner_type, javalang.tree.ClassDeclaration):
                    self._process_class(inner_type)
                elif isinstance(inner_type, javalang.tree.InterfaceDeclaration):
                    self._process_interface(inner_type)
                elif isinstance(inner_type, javalang.tree.EnumDeclaration):
                    self._process_enum(inner_type)
            
            self.classes[full_name] = java_class
            
        finally:
            # Restore previous class context
            self._current_class = prev_class
    
    def _process_interface(self, interface_node: javalang.tree.InterfaceDeclaration):
        """Process an interface declaration."""
        interface_name = interface_node.name
        full_name = f"{self.package}.{interface_name}" if self.package else interface_name
        
        java_interface = JavaClass(
            name=interface_name,
            package=self.package,
            is_interface=True,
            is_abstract=True
        )
        
        # Store current class for semantic analysis
        prev_class = self._current_class
        self._current_class = java_interface
        
        try:
            # Process interface methods
            for method in interface_node.methods:
                self._process_method(method, java_interface)
            
            self.classes[full_name] = java_interface
            
        finally:
            # Restore previous class context
            self._current_class = prev_class
    
    def _process_method(self, method_node, parent_class: JavaClass) -> None:
        """Process a method declaration with detailed semantic information."""
        if not self._current_class:
            return
            
        method_name = method_node.name
        return_type = self._resolve_type(method_node.return_type) if method_node.return_type else "void"
        
        # Process parameters with type information
        parameters = []
        parameter_names = []
        parameter_types = []
        
        for param in method_node.parameters:
            param_type = self._resolve_type(param.type)
            parameters.append(f"{param_type} {param.name}")
            parameter_names.append(param.name)
            parameter_types.append(param_type)
        
        # Create method metadata with detailed information
        method = JavaMethod(
            name=method_name,
            parameters=parameters,
            parameter_names=parameter_names,
            parameter_types=parameter_types,
            return_type=return_type,
            modifiers=[m for m in method_node.modifiers or []],
            start_line=method_node.position.line if method_node.position else 0,
            end_line=self._get_end_line(method_node)
        )
        
        # Store current method for semantic analysis
        prev_method = self._current_method
        self._current_method = method
        
        try:
            # Add method to current class
            if self._current_class:
                self._current_class.methods[method_name] = method
            
            # Create variable scope for method body
            self._enter_scope()
            
            # Add parameters to current scope
            for param_name, param_type in zip(parameter_names, parameter_types):
                var_info = VariableInfo(
                    name=param_name,
                    type_name=param_type,
                    is_parameter=True,
                    is_used=True,  # Assume parameters are used unless proven otherwise
                    declaration_line=method.start_line
                )
                self._add_variable(var_info)
            
            # Process method body if it exists
            if hasattr(method_node, 'body') and method_node.body:
                self._process_method_body(method_node.body, method)
                
        finally:
            # Restore previous method context
            self._current_method = prev_method
            self._exit_scope()
    
    def _process_method_body(self, body_node, method: JavaMethod) -> None:
        """Process method body to extract variables, method calls, and semantic information."""
        if not body_node or not hasattr(body_node, 'statements'):
            return
            
        for node in body_node.statements:
            try:
                # Process local variable declarations
                if isinstance(node, javalang.tree.LocalVariableDeclaration):
                    var_type = self._resolve_type(node.type)
                    for declarator in node.declarators:
                        var_info = VariableInfo(
                            name=declarator.name,
                            type_name=var_type,
                            is_field=False,
                            is_used=False,  # Will be updated during semantic analysis
                            declaration_line=node.position.line if node.position else -1
                        )
                        method.variables[declarator.name] = var_info
                        self._add_variable(var_info)
                        
                        # Process initializer if exists
                        if hasattr(declarator, 'initializer') and declarator.initializer:
                            self._process_expression(declarator.initializer, method)
                
                # Process method calls
                elif isinstance(node, javalang.tree.MethodInvocation):
                    self._process_method_call(node, method)
                
                # Process assignments
                elif isinstance(node, javalang.tree.Assignment):
                    self._process_assignment(node, method)
                
                # Process if/for/while/do/switch/try statements
                elif isinstance(node, (javalang.tree.IfStatement, 
                                     javalang.tree.ForStatement,
                                     javalang.tree.WhileStatement,
                                     javalang.tree.DoStatement,
                                     javalang.tree.SwitchStatement,
                                     javalang.tree.TryStatement)):
                    self._process_control_structure(node, method)
                
                # Process return statements
                elif isinstance(node, javalang.tree.ReturnStatement):
                    if node.expression:
                        self._process_expression(node.expression, method)
                
                # Process throw statements
                elif isinstance(node, javalang.tree.ThrowStatement):
                    if node.expression:
                        self._process_expression(node.expression, method)
                
                # Process try-catch-finally blocks
                elif isinstance(node, javalang.tree.TryStatement):
                    self._process_try_statement(node, method)
                
                # Process other statement types as needed
                
            except Exception as e:
                # Log errors but continue processing
                print(f"Error processing statement at line {node.position.line if hasattr(node, 'position') and node.position else 'unknown'}: {str(e)}")
                continue
    
    def _get_end_line(self, node) -> int:
        """Get the end line of a node."""
        if hasattr(node, 'position') and node.position:
            return node.position.line
        return 0
    
    def _extract_package_and_imports(self) -> None:
        """Extract package and import declarations with detailed information."""
        # Reset imports
        self.imports = {}
        self.imported_classes = {}
        self._imported_star = False
        
        # Extract package
        if hasattr(self.tree, 'package') and self.tree.package:
            self.package = self.tree.package.name
        
        # Process imports
        if hasattr(self.tree, 'imports'):
            for imp in self.tree.imports:
                if not imp.path:
                    continue
                    
                self.imports[imp.path] = imp.path
                
                # Handle static imports and wildcards
                if imp.static:
                    # For static imports, we can't resolve them without analyzing the target class
                    continue
                
                # Handle wildcard imports (e.g., java.util.*)
                if imp.path.endswith('.*'):
                    self._imported_star = True
                    continue
                
                # For regular imports, map simple name to full import
                simple_name = imp.path.split('.')[-1]
                self.imported_classes[simple_name] = imp.path
    
    def _build_type_resolution_map(self) -> None:
        """Build a map for resolving simple type names to fully qualified names."""
        # Add java.lang.* by default
        self._type_resolver = {
            'Object': 'java.lang.Object',
            'String': 'java.lang.String',
            'Integer': 'java.lang.Integer',
            'Long': 'java.lang.Long',
            'Double': 'java.lang.Double',
            'Boolean': 'java.lang.Boolean',
            'Void': 'java.lang.Void',
            'Exception': 'java.lang.Exception',
            'RuntimeException': 'java.lang.RuntimeException',
            # Add other common Java types as needed
        }
        
        # Add imported classes
        self._type_resolver.update(self.imported_classes)
        
        # Add classes from the same package
        if self.package:
            for class_name in self.classes.keys():
                simple_name = class_name.split('.')[-1]
                self._type_resolver[simple_name] = class_name
    
    def _resolve_type(self, type_node) -> str:
        """Resolve a type node to a fully qualified type name."""
        if isinstance(type_node, javalang.tree.ReferenceType):
            return self._resolve_type(type_node.type)
        elif isinstance(type_node, javalang.tree.BasicType):
            return type_node.name
        elif isinstance(type_node, javalang.tree.TypeParameter):
            return type_node.name
        elif isinstance(type_node, javalang.tree.VoidType):
            return 'void'
        elif isinstance(type_node, javalang.tree.ArrayType):
            return f"{self._resolve_type(type_node.element_type)}[]"
        else:
            raise ValueError(f"Unsupported type node: {type_node}")
    
    def _enter_scope(self) -> None:
        """Enter a new scope for variable tracking."""
        self._variable_scopes.append({})
    
    def _exit_scope(self) -> None:
        """Exit the current scope for variable tracking."""
        self._variable_scopes.pop()
    
    def _add_variable(self, var_info: VariableInfo) -> None:
        """Add a variable to the current scope."""
        self._variable_scopes[-1][var_info.name] = var_info
    
    def _process_expression(self, expr, method: JavaMethod) -> None:
        """Process an expression to extract variable usages and method calls."""
        if isinstance(expr, javalang.tree.MethodInvocation):
            self._process_method_call(expr, method)
        elif isinstance(expr, javalang.tree.MemberReference):
            var_name = expr.member
            var_info = self._get_variable(var_name)
            if var_info:
                var_info.is_used = True
                var_info.usage_lines.append(expr.position.line if expr.position else -1)
        elif isinstance(expr, javalang.tree.BinaryOperation):
            self._process_expression(expr.operand1, method)
            self._process_expression(expr.operand2, method)
        elif isinstance(expr, javalang.tree.UnaryOperation):
            self._process_expression(expr.operand, method)
        elif isinstance(expr, javalang.tree.Literal):
            pass  # Literals don't affect variable usage
        elif isinstance(expr, javalang.tree.NewArray):
            self._process_expression(expr.element_type, method)
        elif isinstance(expr, javalang.tree.NewClass):
            self._process_expression(expr.constructor, method)
        elif isinstance(expr, javalang.tree.Cast):
            self._process_expression(expr.target, method)
        elif isinstance(expr, javalang.tree.InstanceOf):
            self._process_expression(expr.target, method)
        elif isinstance(expr, javalang.tree.ArraySelector):
            self._process_expression(expr.index, method)
        elif isinstance(expr, javalang.tree.ArrayInitializer):
            for expr in expr.values:
                self._process_expression(expr, method)
        else:
            raise ValueError(f"Unsupported expression type: {type(expr)}")
    
    def _process_method_call(self, method_call, method: JavaMethod) -> None:
        """Process a method call to extract method call information."""
        method_name = method_call.member
        receiver_type = self._resolve_type(method_call.qualifier) if method_call.qualifier else None
        arguments = [self._resolve_type(arg.type) for arg in method_call.arguments]
        line = method_call.position.line if method_call.position else -1
        
        method_call_info = MethodCallInfo(
            method_name=method_name,
            receiver_type=receiver_type,
            arguments=arguments,
            line=line
        )
        method.method_calls.append(method_call_info)
    
    def _process_assignment(self, assignment, method: JavaMethod) -> None:
        """Process an assignment to extract variable usages and updates."""
        var_name = assignment.target.name
        var_info = self._get_variable(var_name)
        if var_info:
            var_info.is_used = True
            var_info.usage_lines.append(assignment.position.line if assignment.position else -1)
            var_info.is_modified = True
    
    def _process_control_structure(self, control_structure, method: JavaMethod) -> None:
        """Process a control structure to extract variable usages and updates."""
        if isinstance(control_structure, javalang.tree.IfStatement):
            self._process_expression(control_structure.condition, method)
        elif isinstance(control_structure, javalang.tree.ForStatement):
            self._process_expression(control_structure.control, method)
        elif isinstance(control_structure, javalang.tree.WhileStatement):
            self._process_expression(control_structure.condition, method)
        elif isinstance(control_structure, javalang.tree.DoStatement):
            self._process_expression(control_structure.condition, method)
        elif isinstance(control_structure, javalang.tree.SwitchStatement):
            self._process_expression(control_structure.selector, method)
        elif isinstance(control_structure, javalang.tree.TryStatement):
            self._process_try_statement(control_structure, method)
    
    def _process_try_statement(self, try_statement, method: JavaMethod) -> None:
        """Process a try-catch-finally block to extract variable usages and updates."""
        for catch_clause in try_statement.catch_clause:
            self._process_expression(catch_clause.parameter, method)
    
    def _get_variable(self, name: str) -> Optional[VariableInfo]:
        """Get a variable by name from the current scope."""
        for scope in reversed(self._variable_scopes):
            if name in scope:
                return scope[name]
        return None
    
    def _get_analysis_result(self) -> Dict[str, Any]:
        """Convert the analysis to a serializable format."""
        return {
            "file_path": self.file_path,
            "package": self.package,
            "imports": list(self.imports),
            "classes": {
                class_name: {
                    "name": cls.name,
                    "package": cls.package,
                    "is_interface": cls.is_interface,
                    "is_abstract": cls.is_abstract,
                    "methods": {
                        method_name: {
                            "name": method.name,
                            "parameters": method.parameters,
                            "return_type": method.return_type,
                            "modifiers": method.modifiers,
                            "start_line": method.start_line,
                            "end_line": method.end_line,
                            "variables": method.variables,
                            "method_calls": list(method.method_calls)
                        }
                        for method_name, method in cls.methods.items()
                    },
                    "fields": cls.fields,
                    "parent_class": cls.parent_class,
                    "interfaces": cls.interfaces
                }
                for class_name, cls in self.classes.items()
            }
        }
    
    def find_method(self, class_name: str, method_name: str) -> Optional[JavaMethod]:
        """Find a method by class and method name."""
        full_name = f"{self.package}.{class_name}" if self.package and "." not in class_name else class_name
        if full_name in self.classes:
            return self.classes[full_name].methods.get(method_name)
        return None
    
    def find_class(self, class_name: str) -> Optional[JavaClass]:
        """Find a class by name."""
        full_name = f"{self.package}.{class_name}" if self.package and "." not in class_name else class_name
        return self.classes.get(full_name)


def analyze_java_file(file_path: str) -> Dict[str, Any]:
    """Convenience function to analyze a Java file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    analyzer = JavaASTAnalyzer(source, file_path)
    return analyzer.analyze()
