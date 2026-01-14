import json
import os
from typing import Dict, List, Optional
import logging

from config import Config

logger = logging.getLogger(__name__)

class BGMSelector:
    """
    BGM智能选择器
    
    功能：
    1. 基于video_style选择合适的BGM
    2. 基于关键词匹配精细化选择
    3. 支持候选BGM评分排序
    """
    
    def __init__(self, library_path: str = None):
        """\n        Initialize BGM Selector\n        \n        Args:\n            library_path: Path to bgm_library.json file\n        """
        self.library_path = library_path or Config.BGM_LIBRARY_PATH
        self.library = self._load_bgm_library()
        
    def _load_bgm_library(self) -> List[Dict]:
        """加载BGM库元数据"""
        try:
            if os.path.exists(self.library_path):
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    library = data.get('bgm_library', [])
                    logger.info(f"Loaded {len(library)} BGM tracks from library")
                    return library
        except Exception as e:
            logger.warning(f"Failed to load BGM library from {self.library_path}: {e}")
        
        # 降级：使用内置BGM列表
        return self._get_builtin_bgm_list()
    
    def _get_builtin_bgm_list(self) -> List[Dict]:
        """内置BGM列表（Fallback）"""
        
        builtin_list = []
        
        # Use BgmConfig's builtin URLs if available
        if hasattr(Config, 'APP_BGM_BUILTIN_URLS'):
            builtin_urls = getattr(Config, 'APP_BGM_BUILTIN_URLS', [])
            if builtin_urls and isinstance(builtin_urls, list):
                for idx, url in enumerate(builtin_urls):
                    builtin_list.append({
                        "id": f"builtin-{idx+1}",
                        "url": url,
                        "style": "cozy",  # Default to cozy style
                        "tags": ["通用"],
                        "emotion": "温馨",
                        "intensity_curve": [0.15, 0.2, 0.25, 0.2, 0.15]  # Default gentle curve
                    })
        
        if not builtin_list:
            # Last resort: hardcoded fallback
            builtin_list = [{
                "id": "default-warm",
                "url": None,  # Will need to be provided externally
                "style": "cozy",
                "tags": ["通用"],
                "emotion": "温馨",
                "intensity_curve": [0.15, 0.2, 0.25, 0.2, 0.15]
            }]
        
        logger.info(f"Using builtin BGM list with {len(builtin_list)} tracks")
        return builtin_list
    
    def select_bgm(
        self, 
        video_style: str = None, 
        script_keywords: List[str] = None, 
        emotion_distribution: Dict[str, int] = None
    ) -> Optional[Dict]:
        """
        智能选择BGM
        
        Args:
            video_style: 视频风格（stunning/cozy/healing）
            script_keywords: 脚本关键词列表（如['江景', '阳光', '温馨']）
            emotion_distribution: 情绪分布统计（如{'惊艳': 3, '温馨': 2}）
        
        Returns:
            选中的BGM元数据字典
        """
        if not self.library:
            logger.warning("BGM library is empty, cannot select BGM")
            return None
        
        # Default values
        video_style = video_style or 'cozy'
        script_keywords = script_keywords or []
        emotion_distribution = emotion_distribution or {}
        
        candidates = []
        
        for bgm in self.library:
            score = self._calculate_match_score(
                bgm, 
                video_style, 
                script_keywords, 
                emotion_distribution
            )
            candidates.append({'bgm': bgm, 'score': score})
        
        # 按评分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        if candidates:
            selected = candidates[0]['bgm']
            logger.info(
                f"Selected BGM: {selected['id']}",
                extra={
                    "event": "bgm.selection.success",
                    "bgm_id": selected['id'],
                    "style": selected.get('style', 'unknown'),
                    "match_score": candidates[0]['score'],
                    "video_style": video_style,
                    "keywords_count": len(script_keywords)
                }
            )
            return selected
        
        logger.warning("No suitable BGM found, returning None")
        return None
    
    def _calculate_match_score(
        self, 
        bgm: Dict, 
        video_style: str, 
        keywords: List[str], 
        emotions: Dict[str, int]
    ) -> float:
        """
        计算BGM与视频的匹配度评分
        
        评分维度：
        1. 风格匹配（50分）：video_style与bgm.style完全匹配
        2. 关键词匹配（30分）：script_keywords与bgm.tags交集数量
        3. 情绪匹配（20分）：主导情绪与bgm.emotion匹配
        
        Returns:
            0-100的评分
        """
        score = 0.0
        
        # 1. 风格匹配（50分）
        bgm_style = bgm.get('style', '').lower()
        video_style_lower = video_style.lower() if video_style else ''
        
        if bgm_style == video_style_lower:
            score += 50
        elif video_style_lower in ['stunning', 'luxury'] and bgm_style == 'stunning':
            score += 40  # 惊艳系和高端系可互通
        elif video_style_lower in ['cozy', 'healing'] and bgm_style in ['cozy', 'healing']:
            score += 40  # 温馨系和治愈系可互通
        elif video_style_lower == '' or bgm_style == '':
            score += 20  # Partial match if style is not specified
        
        # 2. 关键词匹配（30分）
        bgm_tags = set(bgm.get('tags', []))
        keyword_set = set(keywords) if keywords else set()
        overlap = len(bgm_tags & keyword_set)
        score += min(30, overlap * 10)  # 每个匹配关键词+10分，最多30分
        
        # 3. 情绪匹配（20分）
        if emotions:
            dominant_emotion = max(emotions, key=emotions.get)
            bgm_emotion = bgm.get('emotion', '')
            if bgm_emotion == dominant_emotion:
                score += 20
            elif dominant_emotion in ['惊艳', '震撼'] and bgm_emotion in ['惊艳', '震撼']:
                score += 15  # Partial emotion match
        
        return score
    
    def get_bgm_by_id(self, bgm_id: str) -> Optional[Dict]:
        """
        Get BGM metadata by ID
        
        Args:
            bgm_id: BGM ID
            
        Returns:
            BGM metadata dict or None if not found
        """
        for bgm in self.library:
            if bgm.get('id') == bgm_id:
                return bgm
        return None
    
    def is_available(self) -> bool:
        """Check if BGM library is available"""
        return len(self.library) > 0
