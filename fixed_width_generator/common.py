from typing import Any, Callable, Dict, Optional, Tuple


SourceResult = Tuple[str, Dict[str, Any]]
SourceFunction = Callable[[Dict[str, Any], Dict[str, Any]], SourceResult]
NextLineTypeFunction = Callable[[Dict[str, Any], Dict[str, Any]], Optional[str]]
PredicateFunction = Callable[[Dict[str, Any], Dict[str, Any]], bool]
