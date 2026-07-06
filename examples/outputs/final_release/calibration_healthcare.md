# Calibration Questionnaire: Healthcare Prior Authorization

This questionnaire gathers real operational data to calibrate the simulation
for your organization. Fill in as many answers as possible before generating
the configured scenario.

All default values are reasonable industry approximations. The simulation is
only as accurate as the inputs you provide. Unanswered questions will use
the scenario defaults — clearly marked below.

Return completed answers to your consultant for configuration.


## 1. Process Volume

*Establish realistic case volumes for the simulation.*

**monthly_volume** *(required)*: How many cases does your team process per month (average)?
- Unit: cases/month
- Default used if unanswered: *Varies by scenario (see profile defaults).*
- Guidance: Use a 3–6 month trailing average to smooth seasonality.

**Answer:** _______________________________________________

**peak_multiplier**: During peak periods, how much does volume increase above average (e.g. 1.5× = 50% higher)?
- Unit: multiplier
- Default used if unanswered: *1.0 (no peak modeled by default).*
- Guidance: Useful for setting the conservative profile.

**Answer:** _______________________________________________

**arrival_pattern**: Are cases spread evenly throughout the day or do they arrive in batches?
- Unit: minutes between arrivals (average)
- Default used if unanswered: *Unconstrained (no arrival interval).*
- Guidance: Set to None for unconstrained (default). Set a number to enable queueing.

**Answer:** _______________________________________________


## 2. Staffing and Cost

*Replace default actor costs with your organization's actual labor rates.*

**fully_loaded_cost** *(required)*: What is the fully-loaded hourly cost per FTE for each role involved? (Salary + benefits + overhead, divided by 2,080 hours/year.)
- Unit: $/hour per role
- Default used if unanswered: *Scenario-specific defaults (see actor list in scenario docs).*
- Guidance: List each role separately. Includes: direct labor, benefits (typically 30–40% of salary), and allocated overhead.

**Answer:** _______________________________________________

**fte_count**: How many FTEs are currently allocated to this process?
- Unit: FTEs
- Default used if unanswered: *Not modeled (simulation treats each actor independently).*
- Guidance: This helps contextualize cycle-time and utilization outputs.

**Answer:** _______________________________________________

**daily_capacity**: How many productive hours per day does each role dedicate to this process?
- Unit: hours/day
- Default used if unanswered: *8 hours/day for humans; 24 hours/day for AI agents.*
- Guidance: Typically 4–6 hours for roles with other responsibilities.

**Answer:** _______________________________________________


## 3. Cycle Time

*Calibrate how long each step actually takes in your organization.*

**step_durations** *(required)*: For each stage of the process, what is the typical elapsed time from when the work is started to when it is completed? (List each stage.)
- Unit: minutes per stage
- Default used if unanswered: *Scenario-specific defaults (see node list in scenario docs).*
- Guidance: Focus on active work time, not calendar wait time. Use median, not average.

**Answer:** _______________________________________________

**longest_stage**: Which single stage most often determines the overall process cycle time?
- Unit: stage name
- Guidance: This is your primary bottleneck candidate for AI automation.

**Answer:** _______________________________________________


## 4. Failure and Rework

*Understand how often cases fail, are returned, or require rework.*

**overall_failure_rate** *(required)*: What percentage of cases are rejected, returned, or fail outright (not counting intentional denials)?
- Unit: percentage (0–100%)
- Default used if unanswered: *3–6% depending on the scenario.*
- Guidance: Distinguish between intentional business outcomes (e.g. denied claims) and process failures (e.g. data entry errors).

**Answer:** _______________________________________________

**rework_impact**: When a case fails, approximately how long does rework take relative to the original processing time?
- Unit: multiplier (e.g. 1.5 = 50% longer)

**Answer:** _______________________________________________


## 5. AI Escalation Rate

*Estimate how often an AI agent will need to defer to a human.*

**expected_ai_escalation**: Based on your knowledge of similar AI deployments, what escalation rate (% of cases) would you expect from an AI agent in this process?
- Unit: percentage (0–100%)
- Default used if unanswered: *15–30% depending on scenario stage complexity.*
- Guidance: Industry benchmarks vary widely (10–40%). If unsure, use the conservative profile (higher escalation).

**Answer:** _______________________________________________

**escalation_handling_capacity**: How many escalations per day can your human team currently absorb without degrading quality?
- Unit: escalations/day

**Answer:** _______________________________________________


## 6. Compliance and Audit Requirements

*Surface regulatory constraints that affect automation feasibility.*

**human_in_loop_required**: Are there regulatory or contractual requirements mandating human review at any stage?
- Unit: yes/no per stage
- Guidance: Document the specific regulation or contract clause for your records.

**Answer:** _______________________________________________

**audit_trail_requirements**: Are there audit trail requirements (e.g. decision logging) for this process?
- Unit: yes/no

**Answer:** _______________________________________________


## 7. AI Readiness

*Assess your organization's readiness to deploy AI in this process.*

**data_quality** *(required)*: How would you rate the quality and completeness of the input data for this process? (1 = very poor, 5 = excellent)
- Unit: 1–5 rating
- Guidance: Poor data quality is the #1 cause of AI underperformance; use the conservative profile if rating < 3.

**Answer:** _______________________________________________

**existing_ai_tools**: Does your organization already use AI tools in adjacent processes?
- Unit: yes/no with description

**Answer:** _______________________________________________

**ai_vendor**: Do you have a preferred AI vendor or platform for this automation?
- Unit: vendor name and pricing tier

**Answer:** _______________________________________________


## 8. Implementation Constraints

*Establish realistic cost and timeline bounds for the implementation.*

**implementation_cost_estimate** *(required)*: What is your current estimate for one-time implementation cost? (AI platform, integration development, training, change management.)
- Unit: $ total
- Guidance: Break down into: AI platform ($), integration dev ($), training ($), change management ($).

**Answer:** _______________________________________________

**go_live_timeline**: What is the target timeline from project start to go-live?
- Unit: months

**Answer:** _______________________________________________

**rollback_plan**: Is there a plan to revert to the manual process if the AI implementation fails?
- Unit: yes/no

**Answer:** _______________________________________________


---

IMPORTANT: All simulation outputs are directional estimates based on the
assumptions above. They do not constitute a validated business case. Validate
key metrics with real operational data before making investment decisions.