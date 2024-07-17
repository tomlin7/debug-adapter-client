from pydantic import Field

from .base import Response, ResponseBody
from .types import *


class CancelResponse(Response):
    """Response to 'cancel' request."""

    ...


class AttachResponse(Response):
    """Response to 'attach' request."""

    ...


class BreakpointLocationsResponseBody(ResponseBody):
    """Body of a 'breakpointLocations' response."""

    breakpoints: list[BreakpointLocation] = Field(
        ..., description="List of breakpoints."
    )


class BreakpointLocationsResponse(Response):
    """Response to 'breakpointLocations' request."""

    body: BreakpointLocationsResponseBody


class CompletionsResponseBody(ResponseBody):
    """Body of a 'completions' response."""

    targets: list[CompletionItem] = Field(..., description="List of completion items.")


class CompletionsResponse(Response):
    """Response to 'completions' request."""

    body: CompletionsResponseBody


class ConfigurationDoneResponse(Response):
    """Response to 'configurationDone' request."""

    ...


class ContinueResponseBody(ResponseBody):
    """Body of a 'continue' response."""

    allThreadsContinued: Optional[bool] = Field(
        None, description="If all threads were continued."
    )


class ContinueResponse(Response):
    """Response to 'continue' request."""

    body: ContinueResponseBody


class DataBreakpointInfoResponseBody(ResponseBody):
    """Body of a 'dataBreakpoint' response."""

    dataId: Optional[str] = Field(
        None, description="An identifier for the data breakpoint."
    )
    description: str = Field(
        ..., description="A user-visible description of the breakpoint."
    )
    accessTypes: Optional[list[DataBreakpointAccessType]] = Field(
        None, description="The access types of the data breakpoint."
    )
    canPersist: Optional[bool] = Field(
        None, description="Whether the data breakpoint can be persisted."
    )


class DataBreakpointInfoResponse(Response):
    """Response to 'dataBreakpoint' request."""

    body: DataBreakpointInfoResponseBody


class DisassembleResponseBody(ResponseBody):
    """Body of a 'disassemble' response."""

    instructions: list[DisassembledInstruction] = Field(
        ..., description="List of disassembled instructions."
    )


class DisassembleResponse(Response):
    """Response to 'disassemble' request."""

    body: DisassembleResponseBody


class DisconnectResponse(Response):
    """Response to 'disconnect' request."""

    ...


class EvaluateResponseBody(ResponseBody):
    """Body of an 'evaluate' response."""

    result: str = Field(..., description="The result of the evaluation.")
    type: Optional[str] = Field(None, description="The type of the result.")
    presentationHint: Optional[VariablePresentationHint] = Field(
        None, description="The presentation hint of the result."
    )
    variablesReference: int = Field(
        ...,
        description="The reference to the variables of the evaluation result.",
    )
    namedVariables: Optional[int] = Field(
        None, description="The number of named variables."
    )
    indexedVariables: Optional[int] = Field(
        None, description="The number of indexed variables."
    )
    memoryReference: Optional[str] = Field(
        None, description="The memory reference of the result."
    )


class EvaluateResponse(Response):
    """Response to 'evaluate' request."""

    body: EvaluateResponseBody


class ExceptionInfoResponseBody(ResponseBody):
    exceptionID: str = Field(..., description="The exception ID.")
    description: Optional[str] = Field(
        None, description="The description of the exception."
    )
    breakMode: ExceptionBreakMode = Field(
        ..., description="The break mode of the exception."
    )
    details: Optional[ExceptionDetails] = Field(
        None, description="The details of the exception."
    )


class ExceptionInfoResponse(Response):
    """Response to 'exceptionInfo' request."""

    body: ExceptionInfoResponseBody


class GotoResponse(Response):
    """Response to 'goto' request."""

    ...


class GotoTargetsResponseBody(ResponseBody):
    """Body of a 'gotoTargets' response."""

    targets: list[GotoTarget] = Field(..., description="List of goto targets.")


class GotoTargetsResponse(Response):
    """Response to 'gotoTargets' request."""

    body: GotoTargetsResponseBody


class InitializeResponse(Response):
    """Response to 'initialize' request."""

    body: Optional[Capabilities] = Field(
        None, description="The capabilities of the debug adapter."
    )


class LaunchResponse(Response):
    """Response to 'launch' request."""

    ...


class LoadedSourcesResponseBody(ResponseBody):
    """Body of a 'loadedSources' response."""

    sources: list[Source] = Field(..., description="List of loaded sources.")


class LoadedSourcesResponse(Response):
    """Response to 'loadedSources' request."""

    body: LoadedSourcesResponseBody


class ModulesResponseBody(ResponseBody):
    """Body of a 'modules' response."""

    modules: list[Module] = Field(..., description="List of modules.")
    totalModules: Optional[int] = Field(
        None, description="The total number of modules."
    )


class ModulesResponse(Response):
    """Response to 'modules' request."""

    body: ModulesResponseBody


class NextResponse(Response):
    """Response to 'next' request."""

    ...


class PauseResponse(Response):
    """Response to 'pause' request."""

    ...


class ReadMemoryResponseBody(ResponseBody):
    """Body of a 'readMemory' response."""

    address: str = Field(..., description="The address of the memory read.")
    unreadableBytes: Optional[int] = Field(
        None, description="The number of unreadable bytes."
    )
    data: Optional[str] = Field(None, description="The data read from memory.")


class ReadMemoryResponse(Response):
    """Response to 'readMemory' request."""

    body: ReadMemoryResponseBody


class RestartResponse(Response):
    """Response to 'restart' request."""

    ...


class RestartFrameResponse(Response):
    """Response to 'restartFrame' request."""

    ...


class ReverseContinueResponse(Response):
    """Response to 'reverseContinue' request."""

    ...


class ScopesResponseBody(ResponseBody):
    """Body of a 'scopes' response."""

    scopes: list[Scope] = Field(..., description="List of scopes.")


class ScopesResponse(Response):
    """Response to 'scopes' request."""

    body: ScopesResponseBody


class SetBreakpointsResponseBody(ResponseBody):
    """Body of a 'setBreakpoints' response."""

    breakpoints: list[Breakpoint]


class SetBreakpointsResponse(Response):
    """Response to 'setBreakpoints' request."""

    body: SetBreakpointsResponseBody


class SetDataBreakpointsResponseBody(ResponseBody):
    """Body of a 'setDataBreakpoints' response."""

    breakpoints: list[Breakpoint]


class SetDataBreakpointsResponse(Response):
    """Response to 'setDataBreakpoints' request."""

    body: SetDataBreakpointsResponseBody


class SetExceptionBreakpointsResponseBody(ResponseBody):
    """Body of a 'setExceptionBreakpoints' response."""

    breakpoints: list[ExceptionBreakpointsFilter]


class SetExceptionBreakpointsResponse(Response):
    """Response to 'setExceptionBreakpoints' request."""

    body: Optional[SetExceptionBreakpointsResponseBody] = Field(
        None, description="The exception breakpoints."
    )


class StackTraceResponseBody(ResponseBody):
    """Body of a 'stackTrace' response."""

    stackFrames: list[StackFrame]
    totalFrames: int


class StackTraceResponse(Response):
    """Response to 'stackTrace' request."""

    body: StackTraceResponseBody


class StepInResponse(Response):
    """Response to 'stepIn' request."""

    ...


class StepOutResponse(Response):
    """Response to 'stepOut' request."""

    ...


class ThreadsResponseBody(ResponseBody):
    """Body of a 'threads' response."""

    threads: list[Thread]


class ThreadsResponse(Response):
    """Response to 'threads' request."""

    body: ThreadsResponseBody


class VariablesResponseBody(ResponseBody):
    """Body of a 'variables' response."""

    variables: list[Variable]


class VariablesResponse(Response):
    """Response to 'variables' request."""

    body: VariablesResponseBody
