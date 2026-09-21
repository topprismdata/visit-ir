"""VisitIR — 周期拜访计划中间表示. 设计研究阶段; 实现随母项目 Task 1 语义核心合入."""
__version__ = "0.1.0"

from visit_ir.compiler import COMPILER_VERSION, SemanticCompiler  # noqa: F401

__all__ = ["SemanticCompiler", "COMPILER_VERSION", "__version__"]
