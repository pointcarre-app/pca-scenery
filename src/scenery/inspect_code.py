
import ast
import pathlib
import tokenize

# NOTE mad: claude wrote this

def count_line_types(file_path: pathlib.Path) -> dict[str, int]:
    """
    Count the number of code lines, docstring lines, and other lines in a Python file.
    
    Args:
        file_path (str): Path to the Python file to analyze
        
    Returns:
        tuple: (code_lines, docstring_lines, other_lines)
    """
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        
    # Parse the file into an AST
    tree = ast.parse(content)
    
    # Track line numbers for docstrings
    docstring_lines: set[int] = set()
    
    # Extract all docstrings
    extract_docstrings(tree, docstring_lines)
    
    # Tokenize the file to count comments and total lines
    with open(file_path, 'rb') as file:
        tokens = list(tokenize.tokenize(file.readline))
    
    # Get comment lines
    comment_lines = set()
    for token in tokens:
        if token.type == tokenize.COMMENT:
            comment_lines.add(token.start[0])
    
    # Count total lines
    total_lines = max(token.end[0] for token in tokens) if tokens else 0
    
    # Count blank lines
    with open(file_path, 'r', encoding='utf-8') as file:
        blank_lines = set(i+1 for i, line in enumerate(file) 
                            if line.strip() == '')
    
    # Calculate other lines (comments + blank lines)
    other_lines = len(comment_lines.union(blank_lines))
    
    # Calculate code lines (total - docstrings - other)
    code_lines = total_lines - len(docstring_lines) - other_lines
    
    return {"code": code_lines, "docstring": len(docstring_lines), "other": other_lines}


# Helper function to extract docstrings from AST nodes
def extract_docstrings(node: ast.AST, docstring_lines: set) -> set:


    # Check for module, class, and function docstrings
    if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        docstring = ast.get_docstring(node)
        if docstring:
            # Find line range for this docstring
            if hasattr(node, 'body') and node.body and isinstance(node.body[0], ast.Expr):
                doc_node = node.body[0].value
                if isinstance(doc_node, ast.Constant) and isinstance(doc_node.value, str):
                    start_line = doc_node.lineno
                    end_line = start_line + docstring.count('\n')
                    for line_num in range(start_line, end_line + 1):
                        docstring_lines.add(line_num)
    
    # Recursively process all child nodes
    for child in ast.iter_child_nodes(node):
        extract_docstrings(child, docstring_lines)

    return docstring_lines


