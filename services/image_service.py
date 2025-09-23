# File: services/image_service.py
# 功能：图片处理服务
# 实现：处理图片上传、存储、分析和管理

import os
import uuid
import json
import logging
from typing import Dict, Any, Optional, Tuple
from PIL import Image
import io
import base64
from datetime import datetime
from sqlalchemy.orm import Session
from database_models import Image as ImageModel
from llm.qwen_vl_analyzer import qwen_vl_analyzer

logger = logging.getLogger(__name__)

class ImageService:
    """
    图片处理服务
    功能：处理图片上传、存储、分析和管理
    """
    
    def __init__(self):
        self.upload_dir = "uploads/images"
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        
        # 确保上传目录存在
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def save_image(self, image_data: bytes, user_id: int, session_id: str, 
                   original_filename: str = "image.jpg") -> Dict[str, Any]:
        """
        保存图片并进行分析
        :param image_data: 图片数据
        :param user_id: 用户ID
        :param session_id: 会话ID
        :param original_filename: 原始文件名
        :return: 保存结果
        """
        try:
            # 验证图片
            self._validate_image(image_data)
            
            # 生成文件名和路径
            file_id = str(uuid.uuid4())
            file_extension = self._get_file_extension(original_filename)
            filename = f"{file_id}{file_extension}"
            file_path = os.path.join(self.upload_dir, f"user_{user_id}", filename)
            
            # 确保用户目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 保存图片
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            # 获取图片信息
            image_info = self._get_image_info(image_data)
            
            # 分析图片
            analysis_result = qwen_vl_analyzer.analyze_image(image_data)
            
            # 保存到数据库
            image_record = self._save_to_database(
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                file_path=file_path,
                file_size=len(image_data),
                mime_type=image_info['mime_type'],
                width=image_info['width'],
                height=image_info['height'],
                analysis_result=analysis_result
            )
            
            logger.info(f"✅ 图片保存成功: {image_record.id}")
            
            return {
                "success": True,
                "image_id": image_record.id,
                "filename": filename,
                "file_path": file_path,
                "analysis": analysis_result
            }
            
        except Exception as e:
            logger.error(f"❌ 图片保存失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_image(self, image_data: bytes) -> None:
        """
        验证图片数据
        """
        # 检查文件大小
        if len(image_data) > self.max_file_size:
            raise ValueError(f"图片文件过大，最大支持{self.max_file_size // (1024*1024)}MB")
        
        # 检查图片格式
        try:
            image = Image.open(io.BytesIO(image_data))
            mime_type = f"image/{image.format.lower()}"
            if mime_type not in self.allowed_types:
                raise ValueError(f"不支持的图片格式: {mime_type}")
        except Exception as e:
            raise ValueError(f"无效的图片文件: {e}")
    
    def _get_file_extension(self, filename: str) -> str:
        """
        获取文件扩展名
        """
        _, ext = os.path.splitext(filename)
        return ext if ext else '.jpg'
    
    def _get_image_info(self, image_data: bytes) -> Dict[str, Any]:
        """
        获取图片信息
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            return {
                'width': image.width,
                'height': image.height,
                'mime_type': f"image/{image.format.lower()}"
            }
        except Exception as e:
            logger.warning(f"获取图片信息失败: {e}")
            return {
                'width': None,
                'height': None,
                'mime_type': 'image/jpeg'
            }
    
    def _save_to_database(self, user_id: int, session_id: str, filename: str, 
                         file_path: str, file_size: int, mime_type: str, 
                         width: int, height: int, analysis_result: Dict[str, Any]) -> ImageModel:
        """
        保存图片记录到数据库
        """
        from database_models import SessionLocal
        import json
        
        db: Session = SessionLocal()
        try:
            image_record = ImageModel(
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                width=width,
                height=height,
                analysis_result=json.dumps(analysis_result, ensure_ascii=False)
            )
            
            db.add(image_record)
            db.commit()
            db.refresh(image_record)
            
            return image_record
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_image_analysis(self, image_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取图片分析结果
        """
        from database_models import SessionLocal
        
        db: Session = SessionLocal()
        try:
            image_record = db.query(ImageModel).filter(
                ImageModel.id == image_id,
                ImageModel.user_id == user_id
            ).first()
            
            if not image_record:
                return None
            
            analysis_result = json.loads(image_record.analysis_result) if image_record.analysis_result else {}
            return analysis_result
            
        except Exception as e:
            logger.error(f"获取图片分析结果失败: {e}")
            return None
        finally:
            db.close()
    
    def link_image_to_journal(self, image_id: int, journal_id: int, user_id: int) -> bool:
        """
        将图片关联到日记
        """
        from database_models import SessionLocal
        
        db: Session = SessionLocal()
        try:
            image_record = db.query(ImageModel).filter(
                ImageModel.id == image_id,
                ImageModel.user_id == user_id
            ).first()
            
            if not image_record:
                return False
            
            image_record.journal_id = journal_id
            db.commit()
            
            logger.info(f"✅ 图片 {image_id} 已关联到日记 {journal_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"关联图片到日记失败: {e}")
            return False
        finally:
            db.close()

# 全局图片服务实例
image_service = ImageService()
