from typing import Dict, List, TypedDict, Annotated, Optional
import logging
import json
import re

from config import Config
from llm_client import create_llm_client, LITELLM_AVAILABLE

logger = logging.getLogger(__name__)

class ScriptState(TypedDict):
    """
    脚本生成工作流的状态
    """
    # 输入数据
    house_info: Dict
    timeline_data: List[Dict]
    
    # 迭代过程
    current_script: str  # 当前脚本JSON
    iteration: int  # 当前迭代次数
    feedback_history: List[str]  # 历史反馈
    
    # 评审结果
    quality_score: float  # 质量评分（0-100）
    issues: List[Dict]  # 质量问题列表
    passed: bool  # 是否通过
    
    # 输出
    final_script: str

class MultiAgentScriptGenerator:
    """
    多智能体脚本生成器（Phase 2-3）
    
    架构：
    1. ScriptAgent：负责生成脚本
    2. ReviewerAgent：负责质量评审
    3. DirectorAgent：负责迭代决策和改进建议
    
    使用简化的状态机模式（不依赖LangGraph，保持轻量）
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize Multi-Agent Script Generator
        
        Args:
            llm_client: Deprecated, now uses UnifiedLLMClient internally
        """
        self.script_client = create_llm_client("script_agent")
        self.orchestrator_client = create_llm_client("orchestrator_agent")
        self.max_iterations = Config.MULTI_AGENT_MAX_ITERATIONS
        self.quality_threshold = Config.MULTI_AGENT_QUALITY_THRESHOLD
    
    def generate_script_with_multi_agent(
        self, 
        house_info: Dict, 
        timeline_data: List[Dict], 
        initial_script: str = None
    ) -> tuple[str, Dict]:
        """
        使用多智能体工作流生成脚本
        
        Args:
            house_info: 房源信息
            timeline_data: 视觉分析结果
            initial_script: 初始脚本（可选，如果提供则从评审开始）
            
        Returns:
            (final_script_json, metadata) tuple
            metadata包含: iterations, quality_score, issues
        """
        # 初始化状态
        state = {
            'house_info': house_info,
            'timeline_data': timeline_data,
            'current_script': initial_script or '',
            'iteration': 0,
            'feedback_history': [],
            'quality_score': 0.0,
            'issues': [],
            'passed': False,
            'final_script': ''
        }
        
        logger.info(
            "Starting multi-agent script generation workflow",
            extra={
                "event": "multi_agent.workflow.start",
                "max_iterations": self.max_iterations,
                "quality_threshold": self.quality_threshold
            }
        )
        
        # 工作流循环
        while state['iteration'] < self.max_iterations:
            # Step 1: Script Agent - Generate/Improve Script
            if not state['current_script'] or state['feedback_history']:
                state = self._script_agent_node(state)
            
            # Step 2: Reviewer Agent - Quality Check
            state = self._reviewer_agent_node(state)
            
            # Step 3: Check if passed
            if state['passed']:
                logger.info(
                    f"Script passed quality check",
                    extra={
                        "event": "multi_agent.workflow.passed",
                        "iteration": state['iteration'],
                        "quality_score": state['quality_score']
                    }
                )
                break
            
            # Step 4: Director Agent - Generate Feedback (if not passed and not last iteration)
            if state['iteration'] < self.max_iterations:
                state = self._director_agent_node(state)
            else:
                logger.warning(
                    f"Max iterations reached without passing",
                    extra={
                        "event": "multi_agent.workflow.max_iterations",
                        "final_score": state['quality_score']
                    }
                )
        
        # 设置最终脚本
        state['final_script'] = state['current_script']
        
        metadata = {
            'iterations': state['iteration'],
            'quality_score': state['quality_score'],
            'issues': state['issues'],
            'passed': state['passed']
        }
        
        logger.info(
            "Multi-agent workflow completed",
            extra={
                "event": "multi_agent.workflow.complete",
                "iterations": state['iteration'],
                "quality_score": state['quality_score'],
                "passed": state['passed']
            }
        )
        
        return state['final_script'], metadata
    
    def _script_agent_node(self, state: Dict) -> Dict:
        """
        脚本生成Agent节点
        
        职责：
        - 首次调用：生成初稿脚本
        - 迭代调用：根据反馈改进脚本
        """
        logger.info(f"ScriptAgent: Generating script (iteration={state['iteration']})")
        
        try:
            # 构建Prompt
            if state['iteration'] == 0:
                # 首次生成
                prompt = self._build_initial_prompt(state['house_info'], state['timeline_data'])
            else:
                # 迭代改进
                latest_feedback = state['feedback_history'][-1] if state['feedback_history'] else ""
                prompt = self._build_iteration_prompt(
                    state['current_script'],
                    latest_feedback,
                    state['issues']
                )
            
            # 调用LLM生成脚本
            script_json = self._call_llm_for_script(prompt)
            
            # 更新状态
            state['current_script'] = script_json
            state['iteration'] += 1
            
            logger.info(
                "ScriptAgent: Script generated successfully",
                extra={
                    "event": "agent.script.generated",
                    "iteration": state['iteration'],
                    "script_length": len(script_json)
                }
            )
            
        except Exception as e:
            logger.error(f"ScriptAgent failed: {e}")
            # 如果生成失败且没有当前脚本，创建一个fallback
            if not state['current_script']:
                state['current_script'] = self._create_fallback_script(state['timeline_data'])
            state['iteration'] += 1
        
        return state
    
    def _reviewer_agent_node(self, state: Dict) -> Dict:
        """
        评审Agent节点
        
        职责：
        - 检查脚本质量（开场钩子、真实槽点、情绪化表达）
        - 计算质量评分
        - 生成问题列表
        """
        logger.info(f"ReviewerAgent: Reviewing script (iteration={state['iteration']})")
        
        try:
            script_data = json.loads(state['current_script'])
            
            # 执行质量检查
            quality_result = self._perform_quality_check(script_data, state['house_info'])
            
            state['quality_score'] = quality_result['score']
            state['issues'] = quality_result['issues']
            state['passed'] = quality_result['score'] >= self.quality_threshold
            
            logger.info(
                f"ReviewerAgent: Score={quality_result['score']:.1f}, Passed={state['passed']}",
                extra={
                    "event": "agent.review.complete",
                    "iteration": state['iteration'],
                    "score": quality_result['score'],
                    "issues_count": len(quality_result['issues']),
                    "passed": state['passed']
                }
            )
            
        except Exception as e:
            logger.error(f"ReviewerAgent failed: {e}")
            # 失败时给予最低分
            state['quality_score'] = 0.0
            state['issues'] = [{"type": "parse_error", "description": f"Script parsing failed: {e}"}]
            state['passed'] = False
        
        return state
    
    def _director_agent_node(self, state: Dict) -> Dict:
        """
        总导演Agent节点
        
        职责：
        - 分析评审问题
        - 生成改进建议
        - 决策是否继续迭代
        """
        logger.info(f"DirectorAgent: Generating improvement feedback")
        
        try:
            # 生成改进建议
            feedback = self._generate_improvement_feedback(state['issues'], state['current_script'])
            
            state['feedback_history'].append(feedback)
            
            logger.info(
                f"DirectorAgent: Feedback generated",
                extra={
                    "event": "agent.director.feedback",
                    "feedback_length": len(feedback),
                    "issues_count": len(state['issues'])
                }
            )
            
        except Exception as e:
            logger.error(f"DirectorAgent failed: {e}")
            # 提供通用反馈
            state['feedback_history'].append("Please improve the script quality according to the review issues.")
        
        return state
    
    def _build_initial_prompt(self, house_info: Dict, timeline_data: List[Dict]) -> str:
        """
        构建初始脚本生成Prompt
        """
        title = house_info.get('title', '精选房源')
        description = house_info.get('description', '')
        
        # 提取场景信息
        scenes = []
        for idx, asset in enumerate(timeline_data):
            scenes.append({
                'index': idx,
                'asset_id': asset.get('id') or asset.get('asset_id') or f'asset-{idx}',
                'scene': asset.get('scene_label', '未知场景'),
                'emotion': asset.get('emotion', ''),
                'duration': float(asset.get('duration', 5.0))
            })
        
        prompt = f"""# Role
你是一位具有10年经验、500万粉丝的资深探房博主，擅长创作"温情生活风"的短视频脚本，强调真实感和情感共鸣。

# Task
根据提供的房源信息和视觉场景顺序，生成一段45-60秒的探房视频解说脚本。

# 房源信息
- 标题: {title}
- 描述: {description}
- 房源详细: {json.dumps(house_info, ensure_ascii=False)}

# 视觉场景 (按顺序)
{json.dumps(scenes, ensure_ascii=False, indent=2)}

# 脚本结构要求
必须包含以下三个部分：
1. **开场白 (intro_text)**: 大家好 + 房源简介 + 引导语。要求极具吸引力，前3秒必须抓住观众。
2. **片头卡片 (intro_card)**: 结构化信息，用于视频开头的视觉展示。
3. **分段解说词 (segments)**: 对应每个视觉场景，必须包含 asset_id。

# 质量准则
1. **开场钩子**: 使用价格、位置或独特反差作为开头（如"358万！居然能在滨江买到三房？"）。
2. **真实槽点**: 提及具体的数字、尺寸或亮点（如"270度落地窗"、"32㎡大客厅"）。
3. **情绪化表达**: 使用生活化、有温度的语言（如"阳光洒满客厅"、"治愈感拉满"）。
4. **字数控制**: 严格遵守时长限制，每秒约3-4个字。

# Output Format
必须返回 JSON 格式，如下所示：
```json
{{
  "intro_text": "大家好，今天带大家看的是...",
  "intro_card": {{
    "headline": "位置·小区名",
    "specs": "面积 | 户型",
    "highlights": ["卖点1", "卖点2", "卖点3"]
  }},
  "segments": [
    {{
      "asset_id": "asset-xxx",
      "text": "这段场景的解说词...",
      "emotion": "惊艳/温馨/普通",
      "duration": 5.0,
      "visual_prompt": "English visual description for enhancement",
      "audio_cue": "SFX suggestion"
    }}
  ]
}}
```

请直接输出 JSON，不要包含 Markdown 代码块标记或其他解释。
"""
        return prompt
    
    def _build_iteration_prompt(self, current_script: str, feedback: str, issues: List[Dict]) -> str:
        """
        构建迭代改进Prompt
        """
        issues_text = "\n".join([f"- [{i['type']}] {i['description']}" for i in issues])
        
        prompt = f"""# Task
请根据以下反馈改进脚本，修复质量问题。

# 当前脚本
{current_script}

# 质量问题
{issues_text}

# 改进建议
{feedback}

# Output Requirement
1. 必须保持原有的 JSON 结构（包含 intro_text, intro_card, segments）。
2. 确保 asset_id 与原脚本一一对应，不要修改。
3. 请直接输出改进后的完整 JSON，不要包含 Markdown 标记。
"""
        return prompt
    
    def _call_llm_for_script(self, prompt: str) -> str:
        """
        调用LLM生成脚本
        """
        try:
            # Use UnifiedLLMClient for standardized logging and fallback
            response_text = self.script_client.chat(
                messages=[
                    {"role": "system", "content": "你是一位专业的房产视频脚本创作者，只输出JSON格式的脚本。"},
                    {"role": "user", "content": prompt}
                ]
            )
            
            script_text = response_text.strip()
            
            # Clean up markdown code blocks if present
            script_text = re.sub(r'^```json\s*', '', script_text)
            script_text = re.sub(r'\s*```$', '', script_text)
            
            # Validate JSON
            json.loads(script_text)  # Will raise exception if invalid
            
            return script_text
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}", extra={"event": "agent.llm.failed", "error": str(e)})
            raise

    def _perform_quality_check(self, script_data: Dict, house_info: Dict) -> Dict:
        """
        执行脚本质量检查
        
        检查维度：
        1. 开场钩子（20分）
        2. 真实槽点（30分）
        3. 情绪化表达（30分）
        4. 结构完整性（20分）
        """
        score = 0.0
        issues = []
        
        segments = script_data.get('segments', [])
        
        if not segments:
            issues.append({
                "type": "structure",
                "description": "脚本缺少segments字段或为空"
            })
            return {"score": 0.0, "issues": issues}
        
        # 1. 开场钩子检查（20分）
        first_segment = segments[0]
        first_text = first_segment.get('text', '')
        first_emotion = first_segment.get('emotion', '')
        
        if first_emotion in ['惊艳', '震撼'] or '!' in first_text or '？' in first_text:
            score += 20
        elif len(first_text) > 10:
            score += 10
            issues.append({
                "type": "opening_hook",
                "description": "开场不够吸引人，建议使用惊艳镜头或提问式开头"
            })
        else:
            issues.append({
                "type": "opening_hook",
                "description": "开场过于简短，缺乏冲击力"
            })
        
        # 2. 真实槽点检查（30分）
        has_numbers = any(re.search(r'\d+', seg.get('text', '')) for seg in segments)
        has_specific_features = any(
            any(keyword in seg.get('text', '') for keyword in ['㎡', '米', '楼', '层', '间', '景'])
            for seg in segments
        )
        
        if has_numbers and has_specific_features:
            score += 30
        elif has_numbers or has_specific_features:
            score += 15
            issues.append({
                "type": "specific_details",
                "description": "缺少具体的数字或特色描述（如面积、楼层、景观）"
            })
        else:
            issues.append({
                "type": "specific_details",
                "description": "缺少真实槽点，建议添加具体的尺寸、数字等"
            })
        
        # 3. 情绪化表达检查（30分）
        emotional_words = ['温馨', '舒适', '惊艳', '震撼', '美好', '享受', '感受', '体验']
        emotion_count = sum(
            any(word in seg.get('text', '') for word in emotional_words)
            for seg in segments
        )
        
        if emotion_count >= 3:
            score += 30
        elif emotion_count >= 1:
            score += 15
            issues.append({
                "type": "emotional_expression",
                "description": "情绪化表达不足，建议增加温情、感受类词汇"
            })
        else:
            issues.append({
                "type": "emotional_expression",
                "description": "文案过于机械，缺少情感共鸣"
            })
        
        # 4. 结构完整性检查（20分）
        total_duration = sum(seg.get('duration', 0) for seg in segments)
        has_all_required_fields = all(
            seg.get('text') and seg.get('emotion') and seg.get('duration')
            for seg in segments
        )
        
        if has_all_required_fields and 15 <= total_duration <= 60:
            score += 20
        elif has_all_required_fields:
            score += 10
            issues.append({
                "type": "structure",
                "description": f"视频时长{total_duration:.1f}秒不合理（推荐15-60秒）"
            })
        else:
            issues.append({
                "type": "structure",
                "description": "部分segment缺少必要字段（text/emotion/duration）"
            })
        
        return {
            "score": score,
            "issues": issues
        }
    
    def _generate_improvement_feedback(self, issues: List[Dict], current_script: str) -> str:
        """
        使用总导演Agent生成改进建议
        """
        if not issues:
            return "脚本质量良好，无需改进。"
        
        issues_json = json.dumps(issues, ensure_ascii=False, indent=2)
        
        prompt = f"""# Role
你是一位资深房产视频导演，负责审核并改进脚本质量。

# Task
分析评审提出的质量问题，为脚本作者提供具体的改进指导。

# 质量问题
{issues_json}

# 当前脚本内容
{current_script}

# 要求
1. 给出具体的改写建议，而不是笼统的方向。
2. 重点关注如何增强开场钩子、增加真实细节、提升情感共鸣。
3. 直接给出建议内容，语气专业。
"""
        try:
            feedback = self.orchestrator_client.chat(
                messages=[
                    {"role": "system", "content": "你是一位资深的短视频导演，负责指导脚本优化。"},
                    {"role": "user", "content": prompt}
                ]
            )
            return feedback
        except Exception as e:
            logger.warning(f"DirectorAgent LLM call failed, using rule-based feedback: {e}")
            # Fallback to rule-based feedback
            feedback_parts = ["请针对以下问题进行改进：\n"]
            # ... (rest of old logic as fallback)
            for idx, issue in enumerate(issues):
                issue_type = issue['type']
                description = issue['description']
                
                if issue_type == 'opening_hook':
                    feedback_parts.append(f"{idx+1}. 开场钩子问题：{description}\n   建议：使用第一个惊艳镜头（如江景、大空间）作为开场，配合感叹或提问句式。")
                elif issue_type == 'specific_details':
                    feedback_parts.append(f'{idx+1}. 真实槽点问题：{description}\n   建议：添加具体的数字（如"32㎡大客厅"、"270度全景窗"）。')
                elif issue_type == 'emotional_expression':
                    feedback_parts.append(f'{idx+1}. 情绪化表达问题：{description}\n   建议：使用生活化语言（如"阳光洒满客厅，温暖每一个清晨"）。')
                elif issue_type == 'structure':
                    feedback_parts.append(f"{idx+1}. 结构问题：{description}\n   建议：确保所有字段完整，时长控制在15-60秒。")
                else:
                    feedback_parts.append(f"{idx+1}. {description}")
            
            return "\n".join(feedback_parts)
    
    def _create_fallback_script(self, timeline_data: List[Dict]) -> str:
        """
        创建降级脚本（当LLM调用失败时使用）
        """
        segments = []
        for idx, asset in enumerate(timeline_data):
            segment = {
                "asset_id": asset.get('id') or asset.get('asset_id') or f'asset-{idx}',
                "text": asset.get('scene_label', '精彩镜头'),
                "emotion": asset.get('emotion', '普通'),
                "duration": float(asset.get('duration', 3.0)),
                "visual_prompt": "Standard interior shot",
                "audio_cue": None
            }
            segments.append(segment)
        
        fallback = {
            "intro_text": "大家好，今天带大家看一套精选房源，一起来看看吧。",
            "intro_card": {
                "headline": "精选房源",
                "specs": "优质户型",
                "highlights": ["精装修", "采光好"]
            },
            "segments": segments
        }
        
        return json.dumps(fallback, ensure_ascii=False, indent=2)
