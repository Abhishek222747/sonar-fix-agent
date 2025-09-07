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
            if hasattr(self.tree, 'types') and self.tree.types:
                for type_decl in self.tree.types:
                    try:
                        if not hasattr(type_decl, 'name') or not type_decl.name:
                            continue
                            
                        if isinstance(type_decl, javalang.tree.ClassDeclaration):
                            self._process_class(type_decl)
                        elif isinstance(type_decl, javalang.tree.InterfaceDeclaration):
                            self._process_interface(type_decl)
                        elif hasattr(type_decl, 'declarators'):  # Handle enums, annotations, etc.
                            print(f"[AST] Info: Unhandled type declaration: {type(type_decl).__name__}")
                            
                    except Exception as e:
                        print(f"[AST] Warning: Error processing type declaration {getattr(type_decl, 'name', 'unknown')}: {str(e)}")
                        import traceback
                        traceback.print_exc()
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
        try:
            if not hasattr(class_node, 'name') or not class_node.name:
                print("[AST] Warning: Class node missing name attribute")
                return
                
            class_name = class_node.name
            full_name = f"{self.package}.{class_name}" if self.package else class_name
            
            # Get class modifiers safely
            modifiers = []
            if hasattr(class_node, 'modifiers'):
                modifiers = [m.lower() for m in class_node.modifiers or []]
            
            # Create class metadata with detailed information
            java_class = JavaClass(
                name=class_name,
                package=self.package,
                is_interface=False,
                is_abstract='abstract' in modifiers,
                start_line=getattr(class_node, 'position', None).line if hasattr(class_node, 'position') else 0,
                end_line=0  # Will be updated after processing the body
            )
            
            # Store class in the classes dictionary
            self.classes[full_name] = java_class
            
            # Store current class for semantic analysis
            prev_class = self._current_class
            self._current_class = java_class
            
            try:
                # Process class-level annotations
                if hasattr(class_node, 'annotations'):
                    for ann in class_node.annotations:
                        if hasattr(ann, 'name') and hasattr(ann.name, 'name'):
                            java_class.annotations.append(ann.name.name)
                        elif hasattr(ann, 'name'):
                            java_class.annotations.append(str(ann.name))

                # Process type parameters
                if hasattr(class_node, 'type_parameters'):
                    java_class.type_parameters = [tp.name for tp in class_node.type_parameters]

                # Process fields
                if hasattr(class_node, 'fields'):
                    for field in class_node.fields or []:
                        self._process_field(field)
                
                # Process methods
                if hasattr(class_node, 'methods'):
                    for method in class_node.methods or []:
                        self._process_method(method)
                
                # Process constructors
                if hasattr(class_node, 'constructors'):
                    for constructor in class_node.constructors or []:
                        self._process_constructor(constructor)
                
                # Process inner types (classes, interfaces, enums)
                if hasattr(class_node, 'type_declarations'):
                    for inner_type in class_node.type_declarations or []:
                        if isinstance(inner_type, javalang.tree.ClassDeclaration):
                            self._process_class(inner_type)
                        elif isinstance(inner_type, javalang.tree.InterfaceDeclaration):
                            self._process_interface(inner_type)
                        elif isinstance(inner_type, javalang.tree.EnumDeclaration):
                            self._process_enum(inner_type)
                
                # Update end line if not set
                if java_class.end_line == 0 and hasattr(class_node, 'position') and class_node.position:
                    java_class.end_line = class_node.position.line
                            
            except Exception as e:
                print(f"[AST] Error processing class {class_name} members: {str(e)}")
                import traceback
                traceback.print_exc()
                
            # Restore previous class context
            self._current_class = prev_class
            
        except Exception as e:
            print(f"[AST] Critical error processing class: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Ensure we restore the previous class context even in case of error
            if 'prev_class' in locals():
                self._current_class = prev_class

    def _process_interface(self, interface_node):
        """Process an interface declaration."""
        try:
            if not hasattr(interface_node, 'name') or not interface_node.name:
                print("[AST] Warning: Interface node missing name attribute")
                return
                
            interface_name = interface_node.name
            full_name = f"{self.package}.{interface_name}" if self.package else interface_name
            
            # Create interface metadata
            java_interface = JavaClass(
                name=interface_name,
                package=self.package,
                is_interface=True,
                is_abstract=True,  # All interfaces are implicitly abstract
                start_line=getattr(interface_node, 'position', None).line if hasattr(interface_node, 'position') else 0
            )
            
            # Store interface in the classes dictionary
            self.classes[full_name] = java_interface
            
            # Store current class for semantic analysis
            prev_class = self._current_class
            self._current_class = java_interface
            
            try:
                # Process interface-level annotations
                if hasattr(interface_node, 'annotations'):
                    for annotation in interface_node.annotations:
                        try:
                            if hasattr(annotation, 'name') and annotation.name:
                                print(f"[AST] Found interface annotation: {annotation.name}")
                        except Exception as e:
                            print(f"[AST] Warning: Error processing interface annotation: {str(e)}")
                            continue
                
                # Process fields (interface fields are implicitly public static final)
                if hasattr(interface_node, 'fields'):
                    for field in interface_node.fields or []:
                        self._process_field(field)
                
                # Process methods (interface methods are implicitly public abstract)
                if hasattr(interface_node, 'methods'):
                    for method in interface_node.methods or []:
                        self._process_method(method)
                
                # Process inner types (interfaces can contain other interfaces, enums, etc.)
                if hasattr(interface_node, 'type_declarations'):
                    for inner_type in interface_node.type_declarations or []:
                        if isinstance(inner_type, javalang.tree.InterfaceDeclaration):
                            self._process_interface(inner_type)
                        elif isinstance(inner_type, javalang.tree.ClassDeclaration):
                            self._process_class(inner_type)
                        elif isinstance(inner_type, javalang.tree.EnumDeclaration):
                            self._process_enum(inner_type)
                            
            except Exception as e:
                print(f"[AST] Error processing interface {interface_name} members: {str(e)}")
                import traceback
                traceback.print_exc()
                
            # Restore previous class context
            self._current_class = prev_class
            
        except Exception as e:
            print(f"[AST] Critical error processing interface: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def _process_method(self, method_node):
        """Process a method declaration."""
        try:
            if not hasattr(method_node, 'name') or not method_node.name:
                return
                
            # Get method details
            method_name = method_node.name
            
            # Handle return type - check for void first
            return_type = 'void'
            if hasattr(method_node, 'return_type'):
                if method_node.return_type is None:
                    # Constructor case
                    return_type = 'void'
                elif isinstance(method_node.return_type, str) and method_node.return_type.lower() == 'void':
                    return_type = 'void'
                elif hasattr(method_node.return_type, 'name') and method_node.return_type.name == 'void':
                    return_type = 'void'
                else:
                    return_type = self._resolve_type(method_node.return_type)
            
            # Get method modifiers
            modifiers = []
            if hasattr(method_node, 'modifiers'):
                modifiers = [m.lower() for m in method_node.modifiers or []]
            
            # Process parameters
            parameters = []
            parameter_names = []
            parameter_types = []
            
            if hasattr(method_node, 'parameters'):
                for param in method_node.parameters:
                    param_type = self._resolve_type(param.type) if hasattr(param, 'type') else 'Object'
                    param_name = param.name if hasattr(param, 'name') else f"param{len(parameters)}"
                    parameters.append(f"{param_type} {param_name}")
                    parameter_names.append(param_name)
                    parameter_types.append(param_type)
            
            # Create method info
            method_info = JavaMethod(
                name=method_name,
                parameters=parameters,
                parameter_names=parameter_names,
                parameter_types=parameter_types,
                return_type=return_type,
                modifiers=modifiers,
                start_line=getattr(method_node, 'position', None).line if hasattr(method_node, 'position') else 0,
                end_line=0  # Will be updated after processing the body
            )
            
            # Store method in current class
            if self._current_class:
                self._current_class.methods[method_name] = method_info
                
            # Process method body if it exists
            if hasattr(method_node, 'body') and method_node.body and hasattr(method_node.body, 'position'):
                method_info.end_line = method_node.body.position.line if method_node.body.position else 0
            
            return method_info
            
        except Exception as e:
            print(f"[AST] Error processing method {getattr(method_node, 'name', 'unknown')}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _process_constructor(self, constructor_node):
        """Process a constructor declaration."""
        try:
            if not hasattr(constructor_node, 'name') or not constructor_node.name:
                return
                
            # Get constructor details
            class_name = constructor_node.name
            
            # Get constructor modifiers
            modifiers = []
            if hasattr(constructor_node, 'modifiers'):
                modifiers = [m.lower() for m in constructor_node.modifiers or []]
            
            # Process parameters
            parameters = []
            parameter_names = []
            parameter_types = []
            
            if hasattr(constructor_node, 'parameters'):
                for param in constructor_node.parameters:
                    param_type = self._resolve_type(param.type) if hasattr(param, 'type') else 'Object'
                    param_name = param.name if hasattr(param, 'name') else f"param{len(parameters)}"
                    parameters.append(f"{param_type} {param_name}")
                    parameter_names.append(param_name)
                    parameter_types.append(param_type)
            
            # Create constructor info (reusing JavaMethod class for now)
            constructor_info = JavaMethod(
                name=class_name,  # Constructors have the same name as the class
                parameters=parameters,
                parameter_names=parameter_names,
                parameter_types=parameter_types,
                return_type='void',
                modifiers=modifiers,
                start_line=getattr(constructor_node, 'position', None).line if hasattr(constructor_node, 'position') else 0,
                end_line=0  # Will be updated after processing the body
            )
            
            # Store constructor in current class
            if self._current_class:
                self._current_class.methods[f"{class_name}_constructor_{len(parameters)}"] = constructor_info
                
            # Process constructor body if it exists
            if hasattr(constructor_node, 'body') and constructor_node.body and hasattr(constructor_node.body, 'position'):
                constructor_info.end_line = constructor_node.body.position.line if constructor_node.body.position else 0
            
            return constructor_info
            
        except Exception as e:
            print(f"[AST] Error processing constructor: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _process_enum(self, enum_node):
        """Process an enum declaration."""
        try:
            if not hasattr(enum_node, 'name') or not enum_node.name:
                print("[AST] Warning: Enum node missing name attribute")
                return
                
            enum_name = enum_node.name
            full_name = f"{self.package}.{enum_name}" if self.package else enum_name
            
            # Create enum metadata (enums are implicitly final and extend java.lang.Enum)
            java_enum = JavaClass(
                name=enum_name,
                package=self.package,
                is_interface=False,
                is_abstract=False,  # Enums can have abstract methods but are not abstract themselves
                start_line=getattr(enum_node, 'position', None).line if hasattr(enum_node, 'position') else 0
            )
            
            # Store enum in the classes dictionary
            self.classes[full_name] = java_enum
            
            # Store current class for semantic analysis
            prev_class = self._current_class
            self._current_class = java_enum
            
            try:
                # Process enum-level annotations
                if hasattr(enum_node, 'annotations'):
                    for annotation in enum_node.annotations:
                        try:
                            if hasattr(annotation, 'name') and annotation.name:
                                print(f"[AST] Found enum annotation: {annotation.name}")
                        except Exception as e:
                            print(f"[AST] Warning: Error processing enum annotation: {str(e)}")
                            continue
                
                # Process enum constants
                if hasattr(enum_node, 'constants'):
                    for constant in enum_node.constants or []:
                        constant_name = getattr(constant, 'name', None)
                        if constant_name:
                            # Add enum constant as a field
                            java_enum.fields[constant_name] = full_name  # Type is the enum itself
                            java_enum.field_info[constant_name] = VariableInfo(
                                name=constant_name,
                                type_name=full_name,
                                is_field=True,
                                is_used=True,  # Enum constants are always used
                                declaration_line=getattr(constant, 'position', None).line if hasattr(constant, 'position') else 0
                            )
                
                # Process enum fields
                if hasattr(enum_node, 'fields'):
                    for field in enum_node.fields or []:
                        self._process_field(field)
                
                # Process enum constructors
                if hasattr(enum_node, 'constructors'):
                    for constructor in enum_node.constructors or []:
                        self._process_constructor(constructor)
                
                # Process enum methods
                if hasattr(enum_node, 'methods'):
                    for method in enum_node.methods or []:
                        self._process_method(method)
                
                # Process inner types (enums can contain other classes, interfaces, enums)
                if hasattr(enum_node, 'type_declarations'):
                    for inner_type in enum_node.type_declarations or []:
                        if isinstance(inner_type, javalang.tree.ClassDeclaration):
                            self._process_class(inner_type)
                        elif isinstance(inner_type, javalang.tree.InterfaceDeclaration):
                            self._process_interface(inner_type)
                        elif isinstance(inner_type, javalang.tree.EnumDeclaration):
                            self._process_enum(inner_type)
                            
            except Exception as e:
                print(f"[AST] Error processing enum {enum_name} members: {str(e)}")
                import traceback
                traceback.print_exc()
                
            # Restore previous class context
            self._current_class = prev_class
            
        except Exception as e:
            print(f"[AST] Critical error processing enum: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _process_field(self, field_node):
        """Process a field declaration."""
        try:
            if not hasattr(field_node, 'declarators') or not field_node.declarators:
                return
                
            # Get field type
            field_type = self._resolve_type(field_node.type) if hasattr(field_node, 'type') else 'Object'
            
            # Get field modifiers
            modifiers = []
            if hasattr(field_node, 'modifiers'):
                modifiers = [m.lower() for m in field_node.modifiers or []]
            
            # Process each variable declarator
            for declarator in field_node.declarators:
                if not hasattr(declarator, 'name'):
                    continue
                    
                var_info = VariableInfo(
                    name=declarator.name,
                    type_name=field_type,
                    is_field=True,
                    declaration_line=getattr(field_node, 'position', None).line if hasattr(field_node, 'position') else 0
                )
                
                # Store field info in current class/interface
                if self._current_class:
                    self._current_class.fields[declarator.name] = field_type
                    self._current_class.field_info[declarator.name] = var_info
                    
        except Exception as e:
            print(f"[AST] Error processing field: {str(e)}")
            import traceback
            traceback.print_exc()
    
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
        if type_node is None:
            return 'Object'
            
        try:
            # Handle string type directly (common case)
            if isinstance(type_node, str):
                return type_node
                
            # Handle basic types (int, boolean, etc.)
            if hasattr(type_node, '__class__') and 'BasicType' in str(type_node.__class__):
                return type_node.name
                
            # Handle void type (check for name attribute first to avoid AttributeError)
            if hasattr(type_node, 'name') and type_node.name == 'void':
                return 'void'
                
            # Handle reference types (classes, interfaces, arrays)
            if hasattr(type_node, '__class__') and 'ReferenceType' in str(type_node.__class__):
                # Handle array types
                if hasattr(type_node, 'dimensions') and type_node.dimensions:
                    base_type = self._resolve_type(getattr(type_node, 'name', 'Object'))
                    return f"{base_type}{'[]' * len(type_node.dimensions)}"
                
                # Handle simple reference types
                if hasattr(type_node, 'name') and type_node.name:
                    type_name = type_node.name
                    if isinstance(type_name, str):
                        return type_name
                    elif hasattr(type_name, 'name'):
                        return type_name.name
                
                # Handle cases where the type is directly accessible
                if hasattr(type_node, 'type') and type_node.type:
                    return self._resolve_type(type_node.type)
                    
            # Handle type parameters (generics)
            if hasattr(type_node, '__class__') and 'TypeParameter' in str(type_node.__class__):
                if hasattr(type_node, 'name') and type_node.name:
                    return type_node.name
                
            # Handle array types
            if hasattr(type_node, '__class__') and 'ArrayType' in str(type_node.__class__):
                element_type = self._resolve_type(type_node.element_type) if hasattr(type_node, 'element_type') else 'Object'
                return f"{element_type}[]"
                
            # Handle wildcard types (e.g., ? extends Number)
            if hasattr(type_node, 'extends_bound') and type_node.extends_bound:
                return f"? extends {self._resolve_type(type_node.extends_bound)}"
                
            # Handle type arguments (generics)
            if hasattr(type_node, 'arguments') and type_node.arguments:
                type_name = self._resolve_type(type_node.name) if hasattr(type_node, 'name') else 'Object'
                type_args = ', '.join([self._resolve_type(arg) for arg in type_node.arguments])
                return f"{type_name}<{type_args}>"
                
            # Handle simple name references
            if hasattr(type_node, 'name'):
                return type_node.name
                
            # Handle cases where the type is a simple string representation
            if hasattr(type_node, '__str__'):
                return str(type_node)
                
            # Fallback for unknown types
            return 'Object'
            
        except Exception as e:
            print(f"[AST] Error resolving type {type(type_node)}: {str(e)}")
            import traceback
            traceback.print_exc()
            return 'Object'
    
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
