#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep PNM Scoring System Test
Tests single term scoring, full PNM scoring, and stage assessment
"""

import requests
import json
import sys
import time
import uuid
from typing import Dict, List, Tuple

if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

class DeepPNMScoringTester:
    """Deep testing of PNM scoring system"""
    
    def __init__(self):
        self.question_bank = self._load_question_bank()
        self.session_id = f"deep-pnm-test-{uuid.uuid4().hex[:8]}"
        
    def _load_question_bank(self):
        """Load question bank for realistic responses"""
        try:
            with open('app/data/pnm_questions_v2_full.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading question bank: {e}")
            return []
    
    def _get_realistic_responses(self, pnm: str, term: str) -> List[str]:
        """Get realistic responses based on question bank"""
        # Find questions for this PNM/term
        target_questions = []
        for q in self.question_bank:
            if q['routing']['pnm'] == pnm and q['routing']['term'] == term:
                target_questions.append(q)
        
        if not target_questions:
            # Generic responses if no specific questions found
            return self._get_generic_responses(pnm, term)
        
        # Create realistic responses based on actual questions
        responses = []
        for q in target_questions:
            if 'example_answers' in q:
                responses.extend(q['example_answers'])
            
            # Generate responses based on options
            if 'question' in q and 'options' in q['question']:
                options = q['question']['options']
                # Pick some mid-to-high level responses
                for opt in options[-2:]:  # Take higher-level options
                    if opt['label'] and opt['id'] != 'none':
                        response = f"Yes, {opt['label'].lower()}"
                        responses.append(response)
        
        return responses[:5]  # Limit to 5 responses
    
    def _get_generic_responses(self, pnm: str, term: str) -> List[str]:
        """Get generic responses for PNM/term combinations"""
        base_responses = {
            'Cognitive': {
                'Emergency preparedness': [
                    "Yes, I have a complete emergency plan with backup power",
                    "I've practiced emergency procedures with my caregiver",
                    "I keep emergency contacts and medical info readily available",
                    "I have backup systems for all critical equipment",
                    "We regularly review and update our emergency protocols"
                ],
                'Travel planning': [
                    "I can plan and execute short trips independently", 
                    "I coordinate transportation and accessibility needs",
                    "I research accessible venues before visiting",
                    "I manage travel logistics with my support team",
                    "I help others plan ALS-friendly travel arrangements"
                ]
            },
            'Safety': {
                'Care decision-maker': [
                    "I have designated care decision-makers",
                    "My healthcare proxy is informed and prepared", 
                    "Legal documents are in place and accessible",
                    "My preferences are clearly documented",
                    "Regular discussions with decision-makers occur"
                ],
                'Accessibility': [
                    "Key places in my home are fully accessible",
                    "I've made necessary modifications for safety",
                    "Navigation aids are installed where needed",
                    "Emergency exits are accessible to me",
                    "Regular safety assessments are conducted"
                ]
            },
            'Physiological': {
                'Breathing': [
                    "I use BiPAP machine effectively every night",
                    "I practice breathing exercises regularly",
                    "I monitor my oxygen saturation daily",
                    "I work closely with respiratory therapist",
                    "I have backup ventilation equipment ready"
                ],
                'Mobility': [
                    "I use mobility aids effectively",
                    "I maintain range of motion exercises",
                    "I work with physical therapist regularly", 
                    "I've adapted my environment for mobility",
                    "I use transfer techniques safely"
                ]
            },
            'Esteem': {
                'Home adaptations': [
                    "I've implemented comprehensive home modifications",
                    "Adaptive equipment is working well for me",
                    "I can manage daily tasks with current setup",
                    "I feel confident in my adapted environment",
                    "I help others plan similar adaptations"
                ]
            },
            'Love & Belonging': {
                'Communication': [
                    "I communicate effectively with my support network",
                    "I use adaptive communication tools",
                    "I maintain meaningful relationships",
                    "I participate in community activities",
                    "I share my experiences to help others"
                ]
            }
        }
        
        return base_responses.get(pnm, {}).get(term, [
            f"I'm actively managing {term.lower()} aspects",
            f"I work with professionals on {term.lower()}",
            f"I have good strategies for {term.lower()}",
            f"I feel confident about {term.lower()}",
            f"I help others with {term.lower()} planning"
        ])[:5]
    
    def test_single_term_scoring(self):
        """Test 1: Single PNM Term Scoring"""
        print("\n" + "="*60)
        print("TEST 1: SINGLE PNM TERM SCORING")
        print("="*60)
        
        # Test a specific PNM/term combination
        test_pnm = "Physiological"
        test_term = "Breathing"
        
        print(f"Testing: {test_pnm} -> {test_term}")
        
        try:
            # Start with routing
            route_response = requests.post(
                f"{BASE_URL}/chat/route",
                headers={"X-Session-Id": self.session_id, "Content-Type": "application/json"},
                json={"text": "I have severe breathing problems and use ventilation equipment"}
            )
            
            if route_response.status_code != 200:
                print(f"[FAIL] Routing failed: {route_response.status_code}")
                return False
                
            print(f"[PASS] Routing successful")
            
            # Get realistic responses for this PNM/term
            responses = self._get_realistic_responses(test_pnm, test_term)
            print(f"Using {len(responses)} realistic responses...")
            
            scoring_success = 0
            total_attempts = 0
            
            for i, response in enumerate(responses, 1):
                total_attempts += 1
                print(f"\nResponse {i}: {response[:60]}...")
                
                conv_response = requests.post(
                    f"{BASE_URL}/chat/conversation",
                    headers={"X-Session-Id": self.session_id, "Content-Type": "application/json"},
                    json={"user_response": response}
                )
                
                if conv_response.status_code == 200:
                    # Check session state immediately
                    state_response = requests.get(
                        f"{BASE_URL}/chat/conversation-state",
                        headers={"X-Session-Id": self.session_id}
                    )
                    
                    if state_response.status_code == 200:
                        state_data = state_response.json()
                        scores_count = state_data.get('pnm_scores_count', 0)
                        
                        if scores_count > scoring_success:
                            scoring_success = scores_count
                            print(f"  [SCORE] New score detected! Total scores: {scores_count}")
                        else:
                            print(f"  [INFO] No new score. Total scores: {scores_count}")
                    
                time.sleep(0.5)
            
            print(f"\nSingle Term Scoring Result:")
            print(f"  Responses given: {total_attempts}")
            print(f"  Scores generated: {scoring_success}")
            print(f"  Success: {'YES' if scoring_success > 0 else 'NO'}")
            
            return scoring_success > 0
            
        except Exception as e:
            print(f"[ERROR] Single term scoring test failed: {e}")
            return False
    
    def test_full_pnm_scoring(self):
        """Test 2: Full PNM Domain Scoring"""
        print("\n" + "="*60)
        print("TEST 2: FULL PNM DOMAIN SCORING")
        print("="*60)
        
        # Test multiple terms within a PNM domain
        test_pnm = "Safety"
        test_terms = ["Care decision-maker designation", "Accessibility of key places"]
        
        session_id = f"{self.session_id}-full-pnm"
        
        try:
            total_scores = 0
            
            for term in test_terms:
                print(f"\nTesting: {test_pnm} -> {term}")
                
                # Route for this specific term
                route_response = requests.post(
                    f"{BASE_URL}/chat/route",
                    headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                    json={"text": f"I need help with {term.lower()}"}
                )
                
                if route_response.status_code != 200:
                    continue
                
                # Get responses for this term
                responses = self._get_realistic_responses(test_pnm, term)
                
                for response in responses[:3]:  # Limit to 3 per term
                    conv_response = requests.post(
                        f"{BASE_URL}/chat/conversation",
                        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                        json={"user_response": response}
                    )
                    
                    if conv_response.status_code == 200:
                        # Check scores
                        state_response = requests.get(
                            f"{BASE_URL}/chat/conversation-state",
                            headers={"X-Session-Id": session_id}
                        )
                        
                        if state_response.status_code == 200:
                            state_data = state_response.json()
                            current_scores = state_data.get('pnm_scores_count', 0)
                            if current_scores > total_scores:
                                total_scores = current_scores
                                print(f"  [SCORE] Score for {term}! Total: {current_scores}")
                    
                    time.sleep(0.3)
            
            # Check final PNM profile
            profile_response = requests.get(
                f"{BASE_URL}/chat/pnm-profile",
                headers={"X-Session-Id": session_id}
            )
            
            profile_success = False
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                scores = profile_data.get('scores', [])
                profile = profile_data.get('profile')
                
                if len(scores) > 0:
                    profile_success = True
                    print(f"\n[PROFILE] Generated with {len(scores)} scores")
                    
                    # Show score details
                    for score in scores:
                        pnm = score.get('pnm_level', 'Unknown')
                        domain = score.get('domain', 'Unknown')
                        total = score.get('total_score', 0)
                        percentage = score.get('percentage', 0)
                        print(f"  {pnm}:{domain} = {total}/16 ({percentage:.1f}%)")
            
            print(f"\nFull PNM Domain Scoring Result:")
            print(f"  Terms tested: {len(test_terms)}")
            print(f"  Total scores: {total_scores}")
            print(f"  Profile generated: {'YES' if profile_success else 'NO'}")
            
            return total_scores > 0 and profile_success
            
        except Exception as e:
            print(f"[ERROR] Full PNM scoring test failed: {e}")
            return False
    
    def test_stage_assessment(self):
        """Test 3: Stage Assessment Functionality"""
        print("\n" + "="*60)
        print("TEST 3: STAGE ASSESSMENT")
        print("="*60)
        
        session_id = f"{self.session_id}-stage"
        
        try:
            # Simulate a comprehensive conversation across multiple PNM domains
            pnm_responses = [
                ("Physiological", "I use BiPAP machine and work with respiratory therapist"),
                ("Safety", "I have emergency plans and accessible home setup"),
                ("Cognitive", "I can plan travel and manage emergency preparedness"),
                ("Esteem", "I've implemented home adaptations successfully"),
                ("Love & Belonging", "I communicate well with my support network")
            ]
            
            total_scores = 0
            
            for pnm, response in pnm_responses:
                # Route to this PNM
                route_response = requests.post(
                    f"{BASE_URL}/chat/route",
                    headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                    json={"text": response}
                )
                
                if route_response.status_code == 200:
                    # Make conversation
                    conv_response = requests.post(
                        f"{BASE_URL}/chat/conversation",
                        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                        json={"user_response": response}
                    )
                    
                    if conv_response.status_code == 200:
                        print(f"[CONVERSATION] {pnm}: Processed")
                        
                        # Check scores
                        state_response = requests.get(
                            f"{BASE_URL}/chat/conversation-state",
                            headers={"X-Session-Id": session_id}
                        )
                        
                        if state_response.status_code == 200:
                            state_data = state_response.json()
                            current_scores = state_data.get('pnm_scores_count', 0)
                            if current_scores > total_scores:
                                total_scores = current_scores
                                print(f"  [SCORE] New score! Total: {current_scores}")
                
                time.sleep(0.5)
            
            # Get final profile for stage assessment
            profile_response = requests.get(
                f"{BASE_URL}/chat/pnm-profile",
                headers={"X-Session-Id": session_id}
            )
            
            stage_assessment_success = False
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                scores = profile_data.get('scores', [])
                profile = profile_data.get('profile')
                suggestions = profile_data.get('suggestions', [])
                
                if len(scores) > 0 and profile:
                    stage_assessment_success = True
                    print(f"\n[STAGE ASSESSMENT] Success!")
                    print(f"  Scores across domains: {len(scores)}")
                    print(f"  Awareness profile generated: YES")
                    print(f"  Improvement suggestions: {len(suggestions)}")
                    
                    # Show domain coverage
                    domains = set(score.get('pnm_level', 'Unknown') for score in scores)
                    print(f"  PNM domains covered: {', '.join(domains)}")
            
            print(f"\nStage Assessment Result:")
            print(f"  PNM domains tested: {len(pnm_responses)}")
            print(f"  Total scores generated: {total_scores}")
            print(f"  Stage assessment: {'SUCCESS' if stage_assessment_success else 'FAILED'}")
            
            return stage_assessment_success
            
        except Exception as e:
            print(f"[ERROR] Stage assessment test failed: {e}")
            return False
    
    def run_deep_scoring_tests(self):
        """Run all deep PNM scoring tests"""
        print("Starting Deep PNM Scoring System Tests...")
        print(f"Session: {self.session_id}")
        print(f"Question Bank: {len(self.question_bank)} questions loaded")
        
        results = []
        
        # Run all tests
        test1_result = self.test_single_term_scoring()
        results.append(("Single Term Scoring", test1_result))
        
        test2_result = self.test_full_pnm_scoring()
        results.append(("Full PNM Scoring", test2_result))
        
        test3_result = self.test_stage_assessment()
        results.append(("Stage Assessment", test3_result))
        
        # Final summary
        print("\n" + "="*60)
        print("DEEP PNM SCORING TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\nTest Results:")
        for test_name, success in results:
            status = "PASS" if success else "FAIL"
            print(f"  [{status}] {test_name}")
        
        print(f"\nOverall: {passed}/{total} tests passed ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print("\n[EXCELLENT] All PNM scoring tests passed!")
            print("The scoring system is fully functional.")
        elif success_rate >= 67:
            print(f"\n[GOOD] Most scoring tests passed ({success_rate:.1f}%)")
            print("Core scoring functionality is working.")
        else:
            print(f"\n[NEEDS WORK] Only {success_rate:.1f}% of scoring tests passed")
            print("Scoring system needs debugging.")
        
        return success_rate >= 67

def main():
    tester = DeepPNMScoringTester()
    result = tester.run_deep_scoring_tests()
    return result

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)