# File: services/voice_service.py
# 功能：语音处理服务
# 实现：处理语音识别（ASR）和语音合成（TTS）

import os
import logging
import base64
import requests
import json
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime
import dashscope

logger = logging.getLogger(__name__)

class VoiceService:
    """
    语音处理服务
    功能：处理语音识别（ASR）和语音合成（TTS）
    """
    
    def __init__(self):
        # 阿里云配置（从环境变量读取，使用 .env 文件中已有的配置）
        # 优先使用已有的 API key（如果阿里云百炼语音服务支持使用相同的 API key）
        self.api_key = os.getenv("QIANWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        
        # 如果语音服务需要单独的 AccessKey，可以从环境变量读取（可选）
        self.access_key_id = os.getenv("ALIBABA_ACCESS_KEY_ID")
        self.access_key_secret = os.getenv("ALIBABA_ACCESS_KEY_SECRET")
        self.app_key = os.getenv("ALIBABA_VOICE_APP_KEY")  # 语音服务的AppKey（可选）
        
        # ASR配置
        self.asr_url = "https://nls-gateway.cn-shanghai.aliyuncs.com/stream/v1/asr"
        
        # TTS配置
        self.tts_url = "https://nls-gateway.cn-shanghai.aliyuncs.com/stream/v1/tts"
        
        # 音频格式配置
        self.max_audio_size = 10 * 1024 * 1024  # 10MB
        self.supported_formats = ["wav", "mp3", "m4a", "aac", "pcm"]
        
        # 检查配置
        # 优先使用 API Key（QIANWEN_API_KEY），如果没有则使用 AccessKey
        if not self.api_key and (not self.access_key_id or not self.access_key_secret):
            logger.warning("⚠️ 阿里云语音服务配置缺失，语音功能可能不可用")
    
    def recognize_speech(self, audio_data: bytes, audio_format: str = "wav", language: str = "zh") -> Dict[str, Any]:
        """
        语音识别（ASR）：将语音转换为文本
        
        Args:
            audio_data: 音频数据（字节）
            audio_format: 音频格式（wav, mp3, m4a等）
            language: 识别语言，默认中文（zh），可选：zh（中文）、en（英文）等
            
        Returns:
            识别结果字典，包含文本和置信度
        """
        try:
            # 检查配置：优先使用 API Key，如果没有则使用 AccessKey
            if not self.api_key and (not self.access_key_id or not self.access_key_secret):
                raise ValueError("阿里云语音服务未配置，请设置 QIANWEN_API_KEY 或 ALIBABA_ACCESS_KEY_ID/ALIBABA_ACCESS_KEY_SECRET")
            
            logger.info(f"🎤 开始语音识别，音频大小: {len(audio_data)} bytes, 格式: {audio_format}")
            
            # 验证音频大小
            if len(audio_data) > self.max_audio_size:
                raise ValueError(f"音频文件过大，最大支持 {self.max_audio_size // (1024*1024)}MB")
            
            # 验证格式
            if audio_format.lower() not in self.supported_formats:
                raise ValueError(f"不支持的音频格式: {audio_format}")
            
            # 调用阿里云百炼语音识别API
            # 使用 dashscope MultiModalConversation API（与千问LLM使用相同的API key）
            if not self.api_key:
                raise ValueError("QIANWEN_API_KEY 未配置，无法调用语音识别API")
            
            logger.info("使用 dashscope MultiModalConversation API 调用语音识别")
            
            # 设置dashscope API key和base URL
            dashscope.api_key = self.api_key
            dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
            
            # 由于API需要音频URL，我们需要将base64音频保存为临时文件
            # 然后通过HTTP服务提供访问（需要服务器有公网IP或域名）
            # 保存为临时文件
            import uuid
            import os
            temp_dir = os.path.join(os.getcwd(), "temp_audio")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 生成临时文件名
            temp_filename = f"{uuid.uuid4().hex}.{audio_format}"
            temp_filepath = os.path.join(temp_dir, temp_filename)
            
            # 保存音频文件
            with open(temp_filepath, 'wb') as f:
                f.write(audio_data)
            
            logger.info(f"音频已保存为临时文件: {temp_filepath}")
            
            # 构建音频URL（需要服务器公网URL）
            # 从环境变量获取服务器URL，如果没有则使用默认域名
            server_url = os.getenv("SERVER_URL", "https://emoflow.net.cn")
            # 确保URL格式正确（移除末尾的斜杠）
            server_url = server_url.rstrip('/')
            audio_url = f"{server_url}/temp_audio/{temp_filename}"
            
            logger.info(f"🎤 构建的音频URL: {audio_url}")
            logger.info(f"🎤 服务器URL: {server_url}, 文件名: {temp_filename}")
            
            # 验证URL是否可访问（可选，用于调试）
            # try:
            #     test_response = requests.head(audio_url, timeout=5)
            #     logger.info(f"音频URL可访问性测试: {test_response.status_code}")
            # except Exception as e:
            #     logger.warning(f"音频URL可访问性测试失败: {e}")
            
            # 构建messages（根据示例格式）
            messages = [
                {
                    "role": "system",
                    "content": [
                        {"text": ""}  # 用于配置定制化识别的Context
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"audio": audio_url}  # 使用HTTP URL
                    ]
                }
            ]
            
            # 构建asr_options
            asr_options = {
                "enable_itn": True  # 启用逆文本规范化
            }
            
            # 如果指定了语言，添加到asr_options
            if language:
                asr_options["language"] = language
            
            try:
                # 调用dashscope MultiModalConversation API
                response = dashscope.MultiModalConversation.call(
                    api_key=self.api_key,
                    model="qwen3-asr-flash",  # 使用ASR模型
                    messages=messages,
                    result_format="message",
                    asr_options=asr_options
                )
                
                logger.info(f"ASR API调用完成，状态码: {response.status_code if hasattr(response, 'status_code') else 'N/A'}")
                
                # 检查响应状态
                if response.status_code != 200:
                    error_msg = f"ASR API调用失败: {response.status_code}, {response.message if hasattr(response, 'message') else '未知错误'}"
                    logger.error(error_msg)
                    # 清理临时文件
                    try:
                        if os.path.exists(temp_filepath):
                            os.remove(temp_filepath)
                    except:
                        pass
                    raise Exception(error_msg)
                
                # 解析响应结果
                result = None
                # 根据dashscope响应格式，结果在output中
                if hasattr(response, 'output') and response.output:
                    # 检查是否有choices和message
                    if hasattr(response.output, 'choices') and response.output.choices:
                        choice = response.output.choices[0]
                        if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                            # content可能是文本或列表
                            content = choice.message.content
                            if isinstance(content, list):
                                # 查找文本内容
                                for item in content:
                                    if isinstance(item, dict) and item.get('text'):
                                        recognized_text = item['text']
                                        result = {
                                            "success": True,
                                            "text": recognized_text,
                                            "confidence": 1.0
                                        }
                                        break
                            elif isinstance(content, str):
                                recognized_text = content
                                result = {
                                    "success": True,
                                    "text": recognized_text,
                                    "confidence": 1.0
                                }
                    
                    # 如果格式不同，尝试直接获取text
                    if not result and hasattr(response.output, 'text'):
                        recognized_text = response.output.text
                        result = {
                            "success": True,
                            "text": recognized_text,
                            "confidence": 1.0
                        }
                
                # 清理临时文件
                try:
                    if os.path.exists(temp_filepath):
                        os.remove(temp_filepath)
                        logger.debug(f"临时音频文件已删除: {temp_filepath}")
                except Exception as cleanup_error:
                    logger.warning(f"清理临时文件失败: {cleanup_error}")
                
                if result:
                    return result
                
                # 如果以上都不匹配，记录响应以便调试
                logger.error(f"ASR识别失败: 无法解析响应格式，响应: {response}")
                return {
                    "success": False,
                    "error": "无法解析API响应",
                    "text": None
                }
                    
            except Exception as e:
                # 清理临时文件
                try:
                    if os.path.exists(temp_filepath):
                        os.remove(temp_filepath)
                except:
                    pass
                logger.error(f"ASR API调用异常: {e}")
                import traceback
                traceback.print_exc()
                raise Exception(f"ASR API请求失败: {e}")
                
        except Exception as e:
            logger.error(f"❌ 语音识别失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": None
            }
    
    def synthesize_speech(self, text: str, voice_type: str = "xiaoyun", 
                         audio_format: str = "wav", sample_rate: int = 16000, language: str = "zh") -> Dict[str, Any]:
        """
        语音合成（TTS）：将文本转换为语音
        
        Args:
            text: 要合成的文本
            voice_type: 音色类型（如：xiaoyun中文女声, xiaogang中文男声等），默认xiaoyun（中文）
            audio_format: 音频格式（wav, mp3等）
            sample_rate: 采样率（16000, 8000等）
            language: 合成语言，默认中文（zh），可选：zh（中文）、en（英文）等
            
        Returns:
            合成结果字典，包含音频数据
        """
        try:
            # 检查配置：优先使用 API Key，如果没有则使用 AccessKey
            if not self.api_key and (not self.access_key_id or not self.access_key_secret):
                raise ValueError("阿里云语音服务未配置，请设置 QIANWEN_API_KEY 或 ALIBABA_ACCESS_KEY_ID/ALIBABA_ACCESS_KEY_SECRET")
            
            if not text or len(text.strip()) == 0:
                raise ValueError("文本内容不能为空")
            
            logger.info(f"🔊 开始语音合成，文本长度: {len(text)}, 音色: {voice_type}")
            
            # 调用阿里云百炼语音合成API
            # 使用 dashscope API（与千问LLM使用相同的API key）
            if not self.api_key:
                raise ValueError("QIANWEN_API_KEY 未配置，无法调用语音合成API")
            
            logger.info("使用 dashscope MultiModalConversation API 调用语音合成")
            
            # 设置dashscope API key和base URL
            dashscope.api_key = self.api_key
            dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
            
            # 映射音色类型（根据API文档调整）
            # 默认使用Cherry（中文女声），也可以使用其他音色如Aria、Bella等
            voice_map = {
                "xiaoyun": "Cherry",  # 中文女声
                "xiaogang": "Aria",   # 中文男声（示例，需要根据实际文档调整）
            }
            api_voice = voice_map.get(voice_type, "Cherry")
            
            # 映射语言类型
            language_map = {
                "zh": "Chinese",
                "en": "English"
            }
            api_language = language_map.get(language, "Chinese")
            
            try:
                # 使用SpeechSynthesizer API进行TTS（根据官方示例）
                # 参考：dashscope.audio.qwen_tts.SpeechSynthesizer.call(...)
                from dashscope.audio.qwen_tts import SpeechSynthesizer
                
                response = SpeechSynthesizer.call(
                    api_key=self.api_key,
                    model="qwen3-tts-flash",  # TTS模型
                    text=text,  # 直接传文本
                    voice=api_voice,  # 音色
                    language_type=api_language,  # 语言类型
                    stream=False  # 非流式
                )
                
                logger.info(f"TTS API调用完成，状态码: {response.status_code if hasattr(response, 'status_code') else 'N/A'}")
                
                # 检查响应状态
                if response.status_code != 200:
                    error_msg = f"TTS API调用失败: {response.status_code}, {response.message if hasattr(response, 'message') else '未知错误'}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                # 解析响应结果
                # 根据示例，音频URL在 response.output.audio.url
                # 响应可能是对象或字典格式，需要兼容处理
                audio_url = None
                
                # 方法1: 尝试作为对象属性访问
                try:
                    if hasattr(response, 'output'):
                        output = response.output
                        if hasattr(output, 'audio'):
                            audio = output.audio
                            # audio可能是对象或字典
                            if hasattr(audio, 'url'):
                                audio_url = audio.url
                            elif isinstance(audio, dict):
                                audio_url = audio.get('url')
                except Exception as e:
                    logger.debug(f"对象属性访问失败: {e}")
                
                # 方法2: 如果对象访问失败，尝试字典访问
                if not audio_url:
                    try:
                        # 尝试将响应转换为字典
                        if isinstance(response, dict):
                            response_dict = response
                        elif hasattr(response, '__dict__'):
                            # 如果是对象，尝试获取其字典表示
                            import json
                            response_str = json.dumps(response, default=lambda o: o.__dict__ if hasattr(o, '__dict__') else str(o))
                            response_dict = json.loads(response_str)
                        else:
                            # 尝试直接访问属性并转换为字典
                            response_dict = {
                                'output': getattr(response, 'output', None)
                            }
                        
                        # 从字典中提取URL
                        if response_dict and response_dict.get('output'):
                            output = response_dict['output']
                            if isinstance(output, dict) and output.get('audio'):
                                audio = output['audio']
                                if isinstance(audio, dict):
                                    audio_url = audio.get('url')
                                elif hasattr(audio, 'url'):
                                    audio_url = audio.url
                    except Exception as e:
                        logger.debug(f"字典访问失败: {e}")
                
                # 方法3: 直接使用getattr链式访问（最可靠的方式）
                if not audio_url:
                    try:
                        output = getattr(response, 'output', None)
                        if output:
                            audio = getattr(output, 'audio', None) if hasattr(output, 'audio') else None
                            if not audio and isinstance(output, dict):
                                audio = output.get('audio')
                            
                            if audio:
                                if hasattr(audio, 'url'):
                                    audio_url = audio.url
                                elif isinstance(audio, dict):
                                    audio_url = audio.get('url')
                    except Exception as e:
                        logger.debug(f"getattr链式访问失败: {e}")
                
                if audio_url:
                    logger.info(f"🔊 获取到音频URL: {audio_url}")
                    
                    # 下载音频文件
                    audio_response = requests.get(audio_url, timeout=30)
                    if audio_response.status_code == 200:
                        audio_data = audio_response.content
                        logger.info(f"✅ 音频下载成功，大小: {len(audio_data)} bytes")
                        return {
                            "success": True,
                            "audio_data": audio_data
                        }
                    else:
                        error_msg = f"音频下载失败: {audio_response.status_code}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                else:
                    error_msg = "响应中未找到audio.url字段"
                    logger.error(f"TTS响应解析失败: {error_msg}")
                    logger.error(f"响应类型: {type(response)}")
                    logger.error(f"响应内容: {response}")
                    # 尝试打印响应的结构以便调试
                    try:
                        import json
                        logger.error(f"响应JSON: {json.dumps(response, default=str, ensure_ascii=False)}")
                    except:
                        pass
                    raise Exception(error_msg)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"TTS API请求异常: {e}")
                import traceback
                traceback.print_exc()
                raise Exception(f"TTS API请求失败: {e}")
                
        except Exception as e:
            logger.error(f"❌ 语音合成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "audio_data": None
            }
    
    def decode_base64_audio(self, base64_data: str) -> bytes:
        """
        解码Base64编码的音频数据
        
        Args:
            base64_data: Base64编码的音频数据（可能包含data:audio/wav;base64,前缀）
            
        Returns:
            解码后的音频字节数据
        """
        try:
            # 处理可能包含的data URI前缀
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            # 解码
            audio_data = base64.b64decode(base64_data)
            return audio_data
        except Exception as e:
            logger.error(f"❌ Base64音频解码失败: {e}")
            raise ValueError(f"音频数据解码失败: {e}")
    
    def encode_audio_to_base64(self, audio_data: bytes, mime_type: str = "audio/wav") -> str:
        """
        将音频数据编码为Base64
        
        Args:
            audio_data: 音频字节数据
            mime_type: MIME类型（如 audio/wav, audio/mp3）
            
        Returns:
            Base64编码的字符串（包含data URI前缀）
        """
        try:
            base64_str = base64.b64encode(audio_data).decode('utf-8')
            return f"data:{mime_type};base64,{base64_str}"
        except Exception as e:
            logger.error(f"❌ 音频Base64编码失败: {e}")
            raise ValueError(f"音频编码失败: {e}")

# 全局语音服务实例
voice_service = VoiceService()

