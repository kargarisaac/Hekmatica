###############################################################################
#
#  Welcome to Baml! To use this generated code, please run the following:
#
#  $ pip install baml-py
#
###############################################################################

# This file was generated by BAML: please do not edit it. Instead, edit the
# BAML files and re-generate this code.
#
# ruff: noqa: E501,F401,F821
# flake8: noqa: E501,F401,F821
# pylint: disable=unused-import,line-too-long
# fmt: off
from typing import Any, Dict, List, Optional, Union, TypedDict, Type, Literal
from typing_extensions import NotRequired

import baml_py

from . import types
from .types import Checked, Check
from .type_builder import TypeBuilder


class BamlCallOptions(TypedDict, total=False):
    tb: NotRequired[TypeBuilder]
    client_registry: NotRequired[baml_py.baml_py.ClientRegistry]


class HttpRequest:
    __runtime: baml_py.BamlRuntime
    __ctx_manager: baml_py.BamlCtxManager

    def __init__(self, runtime: baml_py.BamlRuntime, ctx_manager: baml_py.BamlCtxManager):
      self.__runtime = runtime
      self.__ctx_manager = ctx_manager

    
    def AnswerQuestion(
        self,
        question: str,context: List[types.ContextItem],
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "AnswerQuestion",
        {
          "question": question,"context": context,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        False,
      )
    
    def ClarifyQuestion(
        self,
        question: str,
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "ClarifyQuestion",
        {
          "question": question,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        False,
      )
    
    def CritiqueAnswer(
        self,
        question: str,answer: str,
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "CritiqueAnswer",
        {
          "question": question,"answer": answer,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        False,
      )
    
    def GenerateSubqueries(
        self,
        question: str,clarification_details: str,
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "GenerateSubqueries",
        {
          "question": question,"clarification_details": clarification_details,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        False,
      )
    
    def PlanSteps(
        self,
        question: str,subqueries: List[str],
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "PlanSteps",
        {
          "question": question,"subqueries": subqueries,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        False,
      )
    
    def RankResults(
        self,
        question: str,subqueries: List[str],results: List[types.ResultItem],top_k: int,
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "RankResults",
        {
          "question": question,"subqueries": subqueries,"results": results,"top_k": top_k,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        False,
      )
    


class HttpStreamRequest:
    __runtime: baml_py.BamlRuntime
    __ctx_manager: baml_py.BamlCtxManager

    def __init__(self, runtime: baml_py.BamlRuntime, ctx_manager: baml_py.BamlCtxManager):
      self.__runtime = runtime
      self.__ctx_manager = ctx_manager

    
    def AnswerQuestion(
        self,
        question: str,context: List[types.ContextItem],
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "AnswerQuestion",
        {
          "question": question,"context": context,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        True,
      )
    
    def ClarifyQuestion(
        self,
        question: str,
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "ClarifyQuestion",
        {
          "question": question,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        True,
      )
    
    def CritiqueAnswer(
        self,
        question: str,answer: str,
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "CritiqueAnswer",
        {
          "question": question,"answer": answer,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        True,
      )
    
    def GenerateSubqueries(
        self,
        question: str,clarification_details: str,
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "GenerateSubqueries",
        {
          "question": question,"clarification_details": clarification_details,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        True,
      )
    
    def PlanSteps(
        self,
        question: str,subqueries: List[str],
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "PlanSteps",
        {
          "question": question,"subqueries": subqueries,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        True,
      )
    
    def RankResults(
        self,
        question: str,subqueries: List[str],results: List[types.ResultItem],top_k: int,
        baml_options: BamlCallOptions = {},
    ) -> baml_py.HTTPRequest:
      __tb__ = baml_options.get("tb", None)
      if __tb__ is not None:
        tb = __tb__._tb # type: ignore (we know how to use this private attribute)
      else:
        tb = None
      __cr__ = baml_options.get("client_registry", None)

      return self.__runtime.build_request_sync(
        "RankResults",
        {
          "question": question,"subqueries": subqueries,"results": results,"top_k": top_k,
        },
        self.__ctx_manager.get(),
        tb,
        __cr__,
        True,
      )
    


__all__ = ["HttpRequest", "HttpStreamRequest"]