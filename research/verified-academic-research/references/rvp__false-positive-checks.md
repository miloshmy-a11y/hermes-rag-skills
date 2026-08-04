# False Positive Checks — Session Notes

## Case Study: "Workload Among Nurses" Search

### Initial Results: 13 candidate studies
After query expansion + full-text scan, 13 studies matched "workload" + "significant" + "nurses".

### After Content Verification: Only 3 passed

#### ✅ Study 1: 10.1038/s41598-025-05253-0
- New graduate ICU nurses, Saudi Arabia
- Workload was a significant predictor of stress
- Full text confirmed population and finding

#### ✅ Study 2: 10.21834/e-bpj.v9i28.5856
- Nurses in Malaysia public hospitals
- Workload as significant factor contributing to burnout
- Full text confirmed

#### ✅ Study 3: 10.5539/ass.v10n4p67
- Nurses in Malaysia
- "At the top of this list was excessive workload" — ranked #1 stressor
- Full text confirmed with specific ranking statement

### ❌ 9 Studies Excluded

#### 10.1080/20479700.2024.2417641
- Pattern: "significant.*workload" matched
- Content: Workload mentioned as consequence ("amplifying workload on remaining nurses"), not as a significant finding
- Decision: Exclude

#### 10.1186/s12912-022-00852-y
- Pattern: "significantly associated" matched
- Content: Explicitly states "there was no association between workload and job stress"
- Decision: Exclude

#### 10.1080/00140139.2021.2006317 (NASA-TLX validation)
- Pattern: All correct DOIs
- Content: Population is 51 people with Type 1 diabetes, NOT nurses
- Note: "nurses" appears in citations only, describing previous research
- Decision: Exclude (textbook false positive)

#### 10.1155/jonm/6160674
- Pattern: Abstract mentions "significantly influences nursing workloads"
- Content: No full text available; abstract is about patient-nurse ratio influencing workload (background), not workload as finding
- Decision: Exclude

#### 10.1186/s12912-025-03749-8
- Pattern: "significant.*workload" matched
- Content: "high workloads" describes ED characteristics; not a study finding about workload
- Decision: Exclude

#### 10.1186/s12912-024-02203-5
- Pattern: Matched across fields (significant in abstract, workload in tags)
- Content: No "workload" mention in actual text content
- Decision: Exclude

#### 10.3389/fpubh.2024.1370052
- Pattern: "key factor.*workload" matched
- Content: Workload appears as a survey question item ("How important is it... workload"), not as a finding
- Decision: Exclude

#### 10.54729/2789-8296.1131
- Pattern: "significantly associated" with workload
- Content: Study is about emotional intelligence; "dissatisfaction with workload" is mentioned, not workload as a factor
- Decision: Exclude

#### 10.33546/bnj.2556
- Pattern: Multiple workload mentions
- Content: Leadership study; workload is context/challenge for nurse leaders, not a finding about workload's impact on nurses
- Decision: Exclude

## Key Lesson
Always check BOTH:
1. **Population** is the target group (in methods/participants, not just citations)
2. **Finding** is about the concept (in results/discussion, not just mentioned)

DOI verification only confirms #1 of the citation metadata. Content verification is required for both.