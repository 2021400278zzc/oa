from io import BytesIO
from typing import Any

from flask import Response as FlaskResponse
from flask import jsonify

from app.utils.constant import ResponseConstant as R
from app.utils.logger import Log


class Response(R):
    r = R.Object

    def __init__(
        self,
        status_obj: R.Object = None,
        message: str | Exception = "",
        status: str = "",
        code: int | None = None,
        mime_type: str = "",
        data: Any = None,
        immediate: bool = False,
    ) -> None:
        self.message = message
        self.status_obj = status_obj
        self.status = status
        self.code = code
        self.mime_type = mime_type
        self.data = data
        self.immediate = immediate

    def __new__(
        cls,
        status_obj: R.Object = None,
        message: str | Exception = "",
        status: str = "",
        code: int | None = None,
        mime_type: str = "",
        data: Any = None,
        immediate: bool = False,
    ) -> "Response":
        """具有高级特性的构造基本响应体的类
        Args:
            status_obj (R.Object, optional): 状态对象。
            message (str | Exception, optional): 需要发送的消息亦或是需要记录的错误。
            status (str, optional): 需要发送的状态。
            code (int | None, optional): 需要发送的状态码。
            mime_type (str, optional): 响应的mimetype。
            data (Any, optional): 需要发送的数据。
            immediate (bool, optional): 在本次会话中立即返回响应体，默认为False。
        **注意**：在使用状态对象时，传入的状态、状态码、消息的参数仍能应用至响应中。
        当immediate为False时，Response(...)会返回一个实例对象，
        当immediate为True时，Response(...)会在本次请求中返回响应体。
        Example:
        .. code-block:: python
            # 返回标准的成功响应
            return Response(Response.r.OK)
            # 在该请求中立即返回自定义响应体
            return Response(Response.r.AUTH_FAILED, message="密码错误", code=401, immediate=True)
        """
        instance = super().__new__(cls)
        instance.__init__(status_obj, message, status, code, mime_type, data, immediate)

        if immediate:
            return instance.response()  # 立即返回响应
        return instance  # 返回类的实例

    def _get_attributes(
        self, status_obj: R.Object
    ) -> tuple[R.Object, R.Code, R.Message]:
        for key, value in R.Object.__dict__.items():
            if value == status_obj:
                status = status_obj
                code = getattr(R.Code, key)
                message = getattr(R.Message, key)
                return status, code, message

        return R.Object.ERR_INTERNAL, R.Code.ERR_INTERNAL, R.Message.ERR_INTERNAL

    def g_response(self) -> FlaskResponse:
        """将响应转为Flask响应体"""
        message = R.Message.OK
        status = R.Object.OK
        code = R.Code.OK
        err = self.message if isinstance(self.message, Exception) else None

        if self.status_obj:
            status, code, message = self._get_attributes(self.status_obj)

        message = str(self.message) if err else message
        status = self.status or status
        code = self.code if self.code is not None else code

        mime_type = self.mime_type if self.mime_type else None

        if err:
            Log.error(err)

        if isinstance(self.data, (bytes, bytearray, BytesIO)):
            return FlaskResponse(self.data, code, mimetype=mime_type)

        data = jsonify({"msg": message, "status": status, "data": self.data})
        data.mime_type = "application/json"
        return data

    def response(self) -> FlaskResponse:
        """执行响应"""
        return self.g_response()
