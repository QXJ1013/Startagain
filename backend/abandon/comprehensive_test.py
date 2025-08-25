#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合测试脚本 - 测试ALS助手后端的所有关键功能
包括路由、对话流程、PNM评分、信息卡片、档案生成等
"""

import requests
import json
import sys
import time
import uuid

if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

class ALSAssistantTester:
    """ALS助手综合测试类"""
    
    def __init__(self):
        self.session_id = f"comprehensive-test-{uuid.uuid4().hex[:8]}"
        self.test_results = []
        
    def log_result(self, test_name, success, details=""):
        """记录测试结果"""
        status = "PASS" if success else "FAIL"
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "status": status
        }
        self.test_results.append(result)
        print(f"[{status}]: {test_name}")
        if details and not success:
            print(f"    Details: {details}")
        return success
    
    def test_1_routing_and_initialization(self):
        """测试1：路由和初始化"""
        print("\n=== 测试1：路由和初始化 ===")
        
        try:
            # 测试路由功能
            route_response = requests.post(
                f"{BASE_URL}/chat/route",
                headers={"X-Session-Id": self.session_id, "Content-Type": "application/json"},
                json={"text": "我有呼吸困难，需要帮助管理我的ALS症状"}
            )
            
            if route_response.status_code != 200:
                return self.log_result("初始路由", False, f"HTTP {route_response.status_code}")
                
            route_data = route_response.json()
            self.log_result("初始路由", True, f"成功路由到: {route_data.get('pnm', 'Unknown')}")
            
            # 检查会话状态
            state_response = requests.get(
                f"{BASE_URL}/chat/conversation-state",
                headers={"X-Session-Id": self.session_id}
            )
            
            if state_response.status_code == 200:
                state_data = state_response.json()
                return self.log_result("会话初始化", True, 
                    f"PNM: {state_data.get('current_pnm')}, Term: {state_data.get('current_term')}")
            else:
                return self.log_result("会话初始化", False, f"无法获取会话状态")
                
        except Exception as e:
            return self.log_result("路由和初始化", False, str(e))
    
    def test_2_conversation_flow(self):
        """测试2：完整对话流程"""
        print("\n=== 测试2：对话流程和问题回答 ===")
        
        responses = [
            "是的，我使用BiPAP呼吸机进行夜间通气支持",
            "我定期监测血氧饱和度，并与呼吸治疗师合作",
            "我已经制定了紧急情况下的呼吸管理计划",
            "我每天进行膈肌呼吸练习来改善肺功能",
            "我有完善的居家通气设备和备用电源"
        ]
        
        conversation_success = True
        evidence_count = 0
        info_cards_received = 0
        
        try:
            for i, response in enumerate(responses, 1):
                print(f"  回合 {i}: {response[:30]}...")
                
                conv_response = requests.post(
                    f"{BASE_URL}/chat/conversation",
                    headers={"X-Session-Id": self.session_id, "Content-Type": "application/json"},
                    json={"user_response": response}
                )
                
                if conv_response.status_code != 200:
                    conversation_success = False
                    self.log_result(f"对话回合{i}", False, f"HTTP {conv_response.status_code}")
                    continue
                
                conv_data = conv_response.json()
                
                # 记录证据阈值和信息卡片
                if conv_data.get('evidence_threshold_met', False):
                    evidence_count += 1
                
                info_cards = conv_data.get('info_cards', []) or []
                info_cards_received += len(info_cards)
                
                self.log_result(f"对话回合{i}", True, 
                    f"问题: {conv_data.get('question_type', 'unknown')}, 证据阈值: {conv_data.get('evidence_threshold_met', False)}")
                
                time.sleep(0.5)  # 避免请求过快
                
            # 总结对话流程结果
            self.log_result("证据收集", evidence_count > 0, f"达到证据阈值 {evidence_count} 次")
            self.log_result("信息卡片生成", info_cards_received > 0, f"收到 {info_cards_received} 张信息卡片")
            
            return conversation_success
            
        except Exception as e:
            return self.log_result("对话流程", False, str(e))
    
    def test_3_pnm_scoring_accumulation(self):
        """测试3：PNM评分累积和持久化"""
        print("\n=== 测试3：PNM评分系统 ===")
        
        try:
            # 检查会话中的PNM评分
            state_response = requests.get(
                f"{BASE_URL}/chat/conversation-state",
                headers={"X-Session-Id": self.session_id}
            )
            
            if state_response.status_code != 200:
                return self.log_result("PNM评分检查", False, "无法获取会话状态")
            
            state_data = state_response.json()
            scores_count = state_data.get('pnm_scores_count', 0)
            
            self.log_result("PNM评分持久化", scores_count > 0, f"找到 {scores_count} 个评分")
            
            # 获取PNM档案
            profile_response = requests.get(
                f"{BASE_URL}/chat/pnm-profile",
                headers={"X-Session-Id": self.session_id}
            )
            
            if profile_response.status_code != 200:
                return self.log_result("PNM档案生成", False, f"HTTP {profile_response.status_code}")
            
            profile_data = profile_response.json()
            scores = profile_data.get('scores', [])
            profile = profile_data.get('profile')
            suggestions = profile_data.get('suggestions', [])
            
            self.log_result("PNM评分详情", len(scores) > 0, f"档案包含 {len(scores)} 个评分")
            self.log_result("意识档案生成", profile is not None, "生成了PNM意识档案")
            self.log_result("改进建议生成", len(suggestions) > 0, f"生成了 {len(suggestions)} 个改进建议")
            
            # 显示评分详情
            if scores:
                print("    评分详情:")
                for score in scores:
                    pnm_level = score.get('pnm_level', 'Unknown')
                    domain = score.get('domain', 'Unknown')
                    total_score = score.get('total_score', 0)
                    percentage = score.get('percentage', 0)
                    print(f"      {pnm_level}:{domain} = {total_score}/16 ({percentage:.1f}%)")
            
            return len(scores) > 0
            
        except Exception as e:
            return self.log_result("PNM评分系统", False, str(e))
    
    def test_4_info_cards_and_knowledge(self):
        """测试4：信息卡片和知识库功能"""
        print("\n=== 测试4：信息卡片和知识系统 ===")
        
        try:
            # 进行一次专门触发信息卡片的对话
            targeted_response = "我需要了解更多关于呼吸支持设备的信息和最佳实践"
            
            conv_response = requests.post(
                f"{BASE_URL}/chat/conversation",
                headers={"X-Session-Id": self.session_id, "Content-Type": "application/json"},
                json={"user_response": targeted_response}
            )
            
            if conv_response.status_code != 200:
                return self.log_result("信息卡片触发", False, f"HTTP {conv_response.status_code}")
            
            conv_data = conv_response.json()
            info_cards = conv_data.get('info_cards', []) or []
            
            cards_success = len(info_cards) > 0
            self.log_result("信息卡片内容", cards_success, f"收到 {len(info_cards)} 张卡片")
            
            # 检查信息卡片的质量
            if info_cards:
                for i, card in enumerate(info_cards):
                    title = card.get('title', '无标题')
                    bullets = card.get('bullets', [])
                    self.log_result(f"卡片{i+1}质量", len(bullets) > 0, 
                        f"'{title}' 包含 {len(bullets)} 个要点")
            
            return cards_success
            
        except Exception as e:
            return self.log_result("信息卡片和知识", False, str(e))
    
    def test_5_session_persistence(self):
        """测试5：会话持久化"""
        print("\n=== 测试5：会话持久化和状态管理 ===")
        
        try:
            # 获取当前会话状态作为基准
            state_response1 = requests.get(
                f"{BASE_URL}/chat/conversation-state",
                headers={"X-Session-Id": self.session_id}
            )
            
            if state_response1.status_code != 200:
                return self.log_result("会话状态获取", False, "无法获取初始状态")
            
            state1 = state_response1.json()
            
            # 进行一个操作改变状态
            conv_response = requests.post(
                f"{BASE_URL}/chat/conversation",
                headers={"X-Session-Id": self.session_id, "Content-Type": "application/json"},
                json={"user_response": "让我继续这个评估过程"}
            )
            
            if conv_response.status_code != 200:
                return self.log_result("状态变更操作", False, f"HTTP {conv_response.status_code}")
            
            # 再次获取状态
            state_response2 = requests.get(
                f"{BASE_URL}/chat/conversation-state", 
                headers={"X-Session-Id": self.session_id}
            )
            
            if state_response2.status_code != 200:
                return self.log_result("更新状态获取", False, "无法获取更新后状态")
            
            state2 = state_response2.json()
            
            # 验证状态变化
            turn_increased = state2.get('turn_index', 0) > state1.get('turn_index', 0)
            scores_maintained = state2.get('pnm_scores_count', 0) >= state1.get('pnm_scores_count', 0)
            
            self.log_result("对话轮次递增", turn_increased, 
                f"轮次: {state1.get('turn_index')} -> {state2.get('turn_index')}")
            self.log_result("评分持久保持", scores_maintained, 
                f"评分: {state1.get('pnm_scores_count')} -> {state2.get('pnm_scores_count')}")
            
            return turn_increased and scores_maintained
            
        except Exception as e:
            return self.log_result("会话持久化", False, str(e))
    
    def test_6_debug_endpoints(self):
        """测试6：调试端点"""
        print("\n=== 测试6：系统调试功能 ===")
        
        try:
            # 测试问题库状态
            qb_response = requests.get(f"{BASE_URL}/chat/debug-question-bank")
            qb_success = qb_response.status_code == 200
            
            if qb_success:
                qb_data = qb_response.json()
                question_count = qb_data.get('total_questions', 0)
                self.log_result("问题库状态", question_count > 0, f"包含 {question_count} 个问题")
            else:
                self.log_result("问题库状态", False, f"HTTP {qb_response.status_code}")
            
            # 测试会话调试
            debug_response = requests.post(
                f"{BASE_URL}/chat/debug-session",
                headers={"X-Session-Id": self.session_id}
            )
            
            debug_success = debug_response.status_code == 200
            if debug_success:
                debug_data = debug_response.json()
                self.log_result("会话调试", True, 
                    f"会话ID: {debug_data.get('session_object_id')}, 已问问题: {debug_data.get('asked_count')}")
            else:
                self.log_result("会话调试", False, f"HTTP {debug_response.status_code}")
            
            return qb_success and debug_success
            
        except Exception as e:
            return self.log_result("调试端点", False, str(e))
    
    def run_comprehensive_test(self):
        """运行所有综合测试"""
        print("=== 开始ALS助手后端综合测试 ===")
        print(f"会话ID: {self.session_id}")
        print("=" * 60)
        
        # 执行所有测试
        test_methods = [
            self.test_1_routing_and_initialization,
            self.test_2_conversation_flow,
            self.test_3_pnm_scoring_accumulation,
            self.test_4_info_cards_and_knowledge,
            self.test_5_session_persistence,
            self.test_6_debug_endpoints
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                test_name = test_method.__name__.replace('test_', '').replace('_', ' ')
                self.log_result(f"测试执行 - {test_name}", False, str(e))
        
        # 汇总结果
        self.print_summary()
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("=== 测试结果汇总 ===")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r['success'])
        total = len(self.test_results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"总测试项: {total}")
        print(f"通过: {passed}")
        print(f"失败: {total - passed}")
        print(f"成功率: {success_rate:.1f}%")
        
        print(f"\n详细结果:")
        for result in self.test_results:
            print(f"  [{result['status']}]: {result['test']}")
            if result['details']:
                print(f"    {result['details']}")
        
        if success_rate >= 90:
            print(f"\n[优秀] 系统测试通过率达到 {success_rate:.1f}%")
            print("后端系统已准备好用于生产环境!")
        elif success_rate >= 75:
            print(f"\n[良好] 系统测试通过率 {success_rate:.1f}%")
            print("系统基本功能正常，建议解决失败的测试项")
        else:
            print(f"\n[需改进] 系统测试通过率仅 {success_rate:.1f}%")
            print("建议修复关键问题后重新测试")


def main():
    """主测试函数"""
    tester = ALSAssistantTester()
    tester.run_comprehensive_test()


if __name__ == "__main__":
    main()