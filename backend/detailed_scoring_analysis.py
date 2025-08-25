#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细的Term评分、PNM评分和Stage评估效果测试
测试不同水平用户回答的评分准确性和合理性
"""

import os
import sys
import json
from typing import Dict, List, Tuple, Any

# Set encoding for Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

def detailed_scoring_analysis():
    """详细分析Term评分、PNM评分和Stage评估效果"""
    
    print("=" * 80)
    print("详细评分系统效果分析")
    print("=" * 80)
    
    # 准备不同水平的测试用例
    test_scenarios = {
        "初学者水平": {
            "description": "刚诊断ALS，对疾病了解有限",
            "responses": [
                ("我刚被诊断出ALS，还不太了解", "Cognitive", "Learning about ALS/MND"),
                ("医生说我需要用一些设备，但我不确定", "Physiological", "Breathing"),
                ("我有点担心以后会怎样", "Safety", "Emergency preparedness"),
                ("家人都很担心，但我们不知道该怎么办", "Love & Belonging", "Communication"),
                ("我想保持独立，但不知道能做什么", "Esteem", "Independence")
            ]
        },
        "中等水平": {
            "description": "已经了解ALS基础知识，开始使用一些辅助设备",
            "responses": [
                ("我在学习ALS的相关知识，了解这是渐进性疾病", "Cognitive", "Learning about ALS/MND"),
                ("我现在用BiPAP机器帮助呼吸，每晚都用", "Physiological", "Breathing"),
                ("我们制定了紧急情况的计划，备用电源也准备好了", "Safety", "Emergency preparedness"),
                ("我和家人讨论了护理需求，大家都在学习", "Love & Belonging", "Communication"),
                ("我在适应新的生活方式，保持尽可能的自主", "Esteem", "Independence")
            ]
        },
        "高水平": {
            "description": "深度了解ALS，积极管理各方面需求，能指导他人",
            "responses": [
                ("我深入研究了ALS的病理机制和最新治疗方法，参与患者教育", "Cognitive", "Learning about ALS/MND"),
                ("我熟练使用BiPAP和咳痰机，与呼吸治疗师密切合作优化设置", "Physiological", "Breathing"),
                ("我建立了完整的应急预案，包括备用设备和紧急联系网络", "Safety", "Emergency preparedness"),
                ("我帮助其他患者家庭了解ALS，分享经验和资源", "Love & Belonging", "Communication"),
                ("我调整了家居环境，使用辅助技术维持工作和兴趣爱好", "Esteem", "Independence")
            ]
        }
    }
    
    all_results = {}
    
    print("\n1. TERM级别评分详细分析")
    print("=" * 50)
    
    # Test Term-level scoring
    try:
        from app.services.pnm_scoring import PNMScoringEngine
        from app.services.ai_scorer import AIScorer
        
        pnm_engine = PNMScoringEngine()
        ai_scorer = AIScorer()
        
        for level_name, scenario in test_scenarios.items():
            print(f"\n[{level_name}] - {scenario['description']}")
            print("-" * 60)
            
            level_scores = []
            
            for response, pnm, term in scenario['responses']:
                print(f"\n  测试: {pnm} -> {term}")
                print(f"     回答: {response[:60]}...")
                
                # Primary PNM scoring
                try:
                    primary_score = pnm_engine.score_response(response, pnm, term)
                    print(f"     主评分: {primary_score.total_score}/16 ({primary_score.percentage:.1f}%)")
                    print(f"       意识:{primary_score.awareness_score} 理解:{primary_score.understanding_score} 应对:{primary_score.coping_score} 行动:{primary_score.action_score}")
                    level_scores.append(primary_score)
                except Exception as e:
                    print(f"     主评分失败: {e}")
                
                # AI backup scoring
                try:
                    ai_score = ai_scorer.score_response(response, pnm, term)
                    print(f"     AI评分: {ai_score.total_score}/16 ({ai_score.percentage:.1f}%)")
                    print(f"       意识:{ai_score.awareness_score} 理解:{ai_score.understanding_score} 应对:{ai_score.coping_score} 行动:{ai_score.action_score}")
                except Exception as e:
                    print(f"     AI评分失败: {e}")
            
            all_results[level_name] = level_scores
            
            # Level summary
            if level_scores:
                avg_total = sum(s.total_score for s in level_scores) / len(level_scores)
                avg_percentage = sum(s.percentage for s in level_scores) / len(level_scores)
                print(f"\n  {level_name}平均分: {avg_total:.1f}/16 ({avg_percentage:.1f}%)")
        
    except Exception as e:
        print(f"Term级别评分测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n\n2. PNM领域级别聚合分析")
    print("=" * 50)
    
    # Test PNM-level aggregation
    try:
        from app.services.aggregator import aggregate_pnm_scores_from_session
        
        for level_name, scores in all_results.items():
            if not scores:
                continue
                
            print(f"\n[{level_name}] - PNM领域聚合")
            print("-" * 40)
            
            # Aggregate by PNM level
            aggregated = aggregate_pnm_scores_from_session(scores)
            
            for pnm_level, score in aggregated.items():
                percentage = (score / 7.0) * 100
                print(f"  {pnm_level}: {score:.2f}/7.0 ({percentage:.1f}%)")
            
            # Overall average
            overall_avg = sum(aggregated.values()) / len(aggregated) if aggregated else 0
            overall_percentage = (overall_avg / 7.0) * 100
            print(f"  整体平均: {overall_avg:.2f}/7.0 ({overall_percentage:.1f}%)")
        
    except Exception as e:
        print(f"PNM聚合分析失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n\n3. STAGE阶段评估分析")
    print("=" * 50)
    
    # Test Stage assessment
    try:
        from app.services.aggregator import map_stage
        
        for level_name, scores in all_results.items():
            if not scores:
                continue
                
            print(f"\n[{level_name}] - 阶段评估")
            print("-" * 40)
            
            # Get aggregated scores for stage mapping
            aggregated = aggregate_pnm_scores_from_session(scores)
            stages = map_stage(aggregated)
            
            # Display stages
            for pnm_level, stage in stages.items():
                score = aggregated.get(pnm_level, 0)
                print(f"  {pnm_level}: {stage} (评分: {score:.2f}/7.0)")
            
            # Profile analysis
            try:
                profile = pnm_engine.calculate_overall_pnm_profile(scores)
                suggestions = pnm_engine.generate_improvement_suggestions(profile)
                
                if 'overall' in profile:
                    overall = profile['overall']
                    print(f"\n  整体档案:")
                    print(f"    意识水平: {overall['level']}")
                    print(f"    总分: {overall['score']}/{overall['possible']} ({overall['percentage']:.1f}%)")
                
                if suggestions:
                    print(f"\n  改进建议 ({len(suggestions)}条):")
                    for i, suggestion in enumerate(suggestions[:3], 1):
                        print(f"    {i}. {suggestion}")
                        
            except Exception as e:
                print(f"  档案生成失败: {e}")
        
    except Exception as e:
        print(f"Stage评估分析失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n\n4. 评分合理性验证")
    print("=" * 50)
    
    # Validate scoring reasonableness
    try:
        print("\n验证不同水平用户的评分是否合理递增:")
        
        level_averages = {}
        for level_name, scores in all_results.items():
            if scores:
                avg_percentage = sum(s.percentage for s in scores) / len(scores)
                level_averages[level_name] = avg_percentage
                print(f"  {level_name}: {avg_percentage:.1f}%")
        
        # Check if progression makes sense
        if len(level_averages) >= 3:
            beginner = level_averages.get("初学者水平", 0)
            intermediate = level_averages.get("中等水平", 0)
            advanced = level_averages.get("高水平", 0)
            
            print(f"\n评分递增验证:")
            print(f"  初学者 -> 中等: {beginner:.1f}% -> {intermediate:.1f}% {'[PASS]' if intermediate > beginner else '[FAIL]'}")
            print(f"  中等 -> 高水平: {intermediate:.1f}% -> {advanced:.1f}% {'[PASS]' if advanced > intermediate else '[FAIL]'}")
            
            if beginner < intermediate < advanced:
                print("  [SUCCESS] 评分系统能够正确区分不同水平用户！")
            else:
                print("  [WARNING] 评分系统可能需要调整以更好区分用户水平")
        
    except Exception as e:
        print(f"合理性验证失败: {e}")
    
    print("\n\n5. 详细评分维度分析")
    print("=" * 50)
    
    # Detailed dimension analysis
    try:
        dimension_analysis = {
            "awareness_score": "意识维度",
            "understanding_score": "理解维度", 
            "coping_score": "应对维度",
            "action_score": "行动维度"
        }
        
        for level_name, scores in all_results.items():
            if not scores:
                continue
                
            print(f"\n[{level_name}] - 维度分析")
            print("-" * 30)
            
            for dim_attr, dim_name in dimension_analysis.items():
                values = [getattr(score, dim_attr) for score in scores]
                avg_value = sum(values) / len(values)
                avg_percentage = (avg_value / 4.0) * 100
                print(f"  {dim_name}: {avg_value:.1f}/4.0 ({avg_percentage:.1f}%)")
        
        print("\n各维度表现总结:")
        for level_name, scores in all_results.items():
            if not scores:
                continue
            print(f"\n{level_name}:")
            for dim_attr, dim_name in dimension_analysis.items():
                values = [getattr(score, dim_attr) for score in scores]
                avg_value = sum(values) / len(values)
                strength = "强" if avg_value >= 3.0 else "中" if avg_value >= 2.0 else "弱"
                print(f"  {dim_name}: {strength} ({avg_value:.1f}/4)")
        
    except Exception as e:
        print(f"维度分析失败: {e}")
    
    print("\n" + "=" * 80)
    print("详细评分分析完成")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    result = detailed_scoring_analysis()
    sys.exit(0 if result else 1)