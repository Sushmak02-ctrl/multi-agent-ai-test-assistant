
import re
from io import BytesIO

import pandas as pd
import streamlit as st
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


# =========================================================
# 1. APP CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Multi-Agent AI Test Assistant",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 Multi-Agent AI Test Assistant")
st.caption(
    "Requirement analysis, smarter test generation, risk assessment "
    "and QA execution reporting — running locally in Demo Mode."
)

st.info(
    "Demo Mode is rule-based and free to use. "
    "No paid API credits are required."
)


# =========================================================
# 2. CONSTANTS AND HELPERS
# =========================================================

TEST_TYPES = [
    "Positive",
    "Negative",
    "Boundary",
    "Exception",
    "Alternate Path",
]

PRIORITIES = ["Critical", "High", "Medium", "Low"]
EXECUTION_STATUSES = ["Not Run", "Pass", "Fail", "Blocked"]


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def contains_any(text, keywords):
    text = text.lower()
    return any(word in text for word in keywords)


def make_test_case(
    req_id,
    title,
    test_type,
    precondition,
    steps,
    expected,
    test_data,
    priority="Medium",
):
    return {
        "Requirement ID": req_id,
        "Test Case ID": "",
        "Test Scenario": title,
        "Test Type": test_type,
        "Priority": priority,
        "Preconditions": precondition,
        "Test Steps": steps,
        "Test Data": test_data,
        "Expected Result": expected,
        "Status": "Not Run",
        "Actual Result": "",
        "Defect ID": "",
    }


# =========================================================
# 3. REQUIREMENT ANALYSIS AGENT
# =========================================================

def requirement_analyst_agent(requirements):
    findings = []

    vague_words = [
        "fast", "quick", "easy", "user-friendly",
        "appropriate", "efficient", "seamless",
        "simple", "soon", "properly",
    ]

    for req in requirements:
        req_id = req["Requirement ID"]
        text = req["Requirement"]
        lower = text.lower()

        if len(text.split()) < 5:
            findings.append({
                "Requirement ID": req_id,
                "Finding Type": "Potentially incomplete",
                "Severity": "Medium",
                "Finding": "The requirement is very short and may lack "
                           "details needed for testing.",
                "Recommendation": "Clarify the actor, action, conditions "
                                  "and expected result.",
            })

        found_vague = [word for word in vague_words if word in lower]
        if found_vague:
            findings.append({
                "Requirement ID": req_id,
                "Finding Type": "Vague wording",
                "Severity": "Medium",
                "Finding": "Potentially vague terms: "
                           + ", ".join(found_vague),
                "Recommendation": "Replace subjective wording with "
                                  "measurable acceptance criteria.",
            })

        if not contains_any(
            lower,
            ["should", "must", "shall", "can", "allow", "enable",
             "display", "show", "provide", "prevent", "verify",
             "validate", "support", "when", "if"],
        ):
            findings.append({
                "Requirement ID": req_id,
                "Finding Type": "Action may be unclear",
                "Severity": "Low",
                "Finding": "The required system behaviour may not be explicit.",
                "Recommendation": "Describe what the system must do "
                                  "and what result the user should see.",
            })

        if contains_any(lower, ["login", "log in", "sign in", "authenticate"]):
            if not contains_any(
                lower,
                ["invalid", "incorrect", "locked", "failed", "error",
                 "unsuccessful", "attempt"],
            ):
                findings.append({
                    "Requirement ID": req_id,
                    "Finding Type": "Potential missing negative criteria",
                    "Severity": "Medium",
                    "Finding": "Login requirement may not specify "
                               "invalid-credential behaviour.",
                    "Recommendation": "Define the expected response to "
                                      "invalid credentials and repeated failures.",
                })

        if contains_any(
            lower,
            ["transfer", "payment", "payee", "transaction"],
        ):
            if not contains_any(
                lower,
                ["limit", "insufficient", "decline", "failed",
                 "invalid", "balance", "duplicate"],
            ):
                findings.append({
                    "Requirement ID": req_id,
                    "Finding Type": "Potential missing transaction criteria",
                    "Severity": "Medium",
                    "Finding": "The requirement may not define "
                               "transaction failure or validation behaviour.",
                    "Recommendation": "Clarify balance checks, transaction "
                                      "limits, duplicate handling and failures.",
                })

    return pd.DataFrame(
        findings,
        columns=[
            "Requirement ID", "Finding Type", "Severity",
            "Finding", "Recommendation",
        ],
    )


# =========================================================
# 4. SMARTER TEST DESIGNER AGENT
# =========================================================

def test_designer_agent(requirements, selected_types):
    cases = []

    for req in requirements:
        req_id = req["Requirement ID"]
        text = req["Requirement"]
        lower = text.lower()

        is_login = contains_any(
            lower,
            ["login", "log in", "sign in", "authenticate", "password"],
        )
        is_transfer = contains_any(
            lower,
            ["transfer", "payment", "payee", "transaction", "funds"],
        )
        is_registration = contains_any(
            lower,
            ["register", "registration", "profile", "sign up", "account creation"],
        )
        is_checkout = contains_any(
            lower,
            ["checkout", "cart", "purchase", "order", "shopping"],
        )
        is_search = contains_any(
            lower,
            ["search", "filter", "sort", "find records"],
        )

        # Choose domain-specific scenarios.
        if is_login:
            scenarios = [
                (
                    "Positive", "Login with valid credentials",
                    "A registered, active user exists.",
                    "1. Open the login page.\n"
                    "2. Enter valid credentials.\n"
                    "3. Select Login.",
                    "The user is authenticated and redirected to the "
                    "appropriate page.",
                    "Username: valid_user\nPassword: valid_password",
                    "High",
                ),
                (
                    "Negative", "Login with invalid credentials",
                    "The login page is available.",
                    "1. Open the login page.\n"
                    "2. Enter an invalid password.\n"
                    "3. Select Login.",
                    "Access is denied and an appropriate error message "
                    "is displayed.",
                    "Username: valid_user\nPassword: incorrect_password",
                    "High",
                ),
                (
                    "Boundary", "Validate empty login fields",
                    "The login page is available.",
                    "1. Leave the username and password empty.\n"
                    "2. Select Login.",
                    "Required-field validation is displayed and login "
                    "is not completed.",
                    "Username: blank\nPassword: blank",
                    "Medium",
                ),
                (
                    "Exception", "Handle authentication service failure",
                    "The authentication service is unavailable or times out.",
                    "1. Open the login page.\n"
                    "2. Submit valid-looking credentials.\n"
                    "3. Simulate or observe a service failure in an "
                    "authorised test environment.",
                    "The application handles the failure gracefully and "
                    "does not grant unauthorised access.",
                    "Valid-format credentials; simulated service failure",
                    "High",
                ),
                (
                    "Alternate Path", "Recover from a failed login",
                    "A registered user has entered incorrect credentials.",
                    "1. Submit incorrect credentials.\n"
                    "2. Correct the credentials.\n"
                    "3. Submit again.",
                    "The user can authenticate successfully after "
                    "correcting the credentials, subject to security rules.",
                    "First attempt: incorrect password\nSecond attempt: valid password",
                    "Medium",
                ),
            ]

        elif is_transfer:
            scenarios = [
                (
                    "Positive", "Complete a valid funds transfer",
                    "The user is authenticated, the payee is valid and "
                    "sufficient funds are available.",
                    "1. Open the transfer page.\n"
                    "2. Select a valid payee.\n"
                    "3. Enter a valid amount.\n"
                    "4. Review and confirm the transfer.",
                    "The transfer is processed once and a confirmation "
                    "or transaction reference is provided.",
                    "Valid payee; amount within permitted limit; sufficient balance",
                    "Critical",
                ),
                (
                    "Negative", "Reject an invalid transfer amount",
                    "The user is authenticated and the transfer page is open.",
                    "1. Enter zero, a negative amount or invalid text.\n"
                    "2. Attempt to continue.",
                    "Validation prevents an invalid transfer and no funds "
                    "are moved.",
                    "Amount: 0 / -10 / invalid text",
                    "High",
                ),
                (
                    "Boundary", "Validate transfer amount at configured limit",
                    "The permitted transaction limit is known.",
                    "1. Enter an amount at the permitted limit.\n"
                    "2. Submit the transfer.\n"
                    "3. Repeat with an amount just above the limit.",
                    "The boundary value is handled according to the "
                    "configured policy; an over-limit transfer is rejected "
                    "when the policy prohibits it.",
                    "Limit amount; limit plus smallest currency unit",
                    "High",
                ),
                (
                    "Exception", "Handle a transfer processing failure",
                    "The user is authenticated and a valid transfer is prepared.",
                    "1. Submit a valid transfer in an authorised test environment.\n"
                    "2. Simulate or observe a processing timeout or service error.\n"
                    "3. Check transaction status and account balances.",
                    "The application provides a clear outcome and avoids "
                    "an unintended duplicate debit or transfer.",
                    "Valid transfer; simulated timeout or service failure",
                    "Critical",
                ),
                (
                    "Alternate Path", "Cancel a transfer before confirmation",
                    "The user is reviewing transfer details.",
                    "1. Enter valid transfer details.\n"
                    "2. Choose Cancel or navigate back before confirmation.\n"
                    "3. Check transaction history and balances.",
                    "The unconfirmed transfer is not processed and balances "
                    "remain unchanged.",
                    "Valid payee and amount; cancel before final confirmation",
                    "Medium",
                ),
            ]

        elif is_registration:
            scenarios = [
                (
                    "Positive", "Submit valid registration details",
                    "The registration page is available.",
                    "1. Open registration.\n"
                    "2. Enter valid required details.\n"
                    "3. Submit the form.",
                    "The registration succeeds and the expected confirmation "
                    "or next step is displayed.",
                    "Unique email; valid required fields",
                    "High",
                ),
                (
                    "Negative", "Reject invalid registration details",
                    "The registration page is available.",
                    "1. Enter an invalid email or invalid required field.\n"
                    "2. Submit the form.",
                    "The invalid data is rejected and helpful validation "
                    "messages are shown.",
                    "Invalid email; malformed field value",
                    "High",
                ),
                (
                    "Boundary", "Validate field length limits",
                    "Field length rules are defined.",
                    "1. Enter values at the minimum and maximum allowed lengths.\n"
                    "2. Repeat with values outside the limits.",
                    "Values are accepted or rejected according to the "
                    "documented field constraints.",
                    "Minimum length; maximum length; one character over limit",
                    "Medium",
                ),
                (
                    "Exception", "Handle registration service failure",
                    "The registration page is available.",
                    "1. Submit valid registration details.\n"
                    "2. Simulate or observe a server failure in a test environment.",
                    "The failure is handled safely and the user receives "
                    "an appropriate message.",
                    "Valid registration details; simulated service failure",
                    "High",
                ),
                (
                    "Alternate Path", "Return to registration and correct details",
                    "The form contains a validation error.",
                    "1. Submit a form with one invalid field.\n"
                    "2. Correct that field.\n"
                    "3. Submit again.",
                    "The corrected form can be submitted successfully.",
                    "One invalid field followed by corrected value",
                    "Medium",
                ),
            ]

        elif is_checkout:
            scenarios = [
                (
                    "Positive", "Complete a valid checkout",
                    "The cart contains an available item and checkout is enabled.",
                    "1. Open the cart.\n"
                    "2. Review quantities and totals.\n"
                    "3. Enter valid delivery and payment details.\n"
                    "4. Confirm the order.",
                    "The order is created once and the correct confirmation "
                    "and total are displayed.",
                    "Available item; valid address; valid test payment method",
                    "High",
                ),
                (
                    "Negative", "Prevent checkout with invalid details",
                    "The cart contains an item.",
                    "1. Enter invalid or missing required checkout details.\n"
                    "2. Attempt to place the order.",
                    "Checkout is blocked and the relevant fields are identified.",
                    "Missing address or invalid payment test data",
                    "High",
                ),
                (
                    "Boundary", "Validate quantity boundaries",
                    "The item quantity rules are defined.",
                    "1. Enter the minimum permitted quantity.\n"
                    "2. Enter the maximum permitted quantity.\n"
                    "3. Try values outside the permitted range.",
                    "Quantity rules are enforced and totals remain correct.",
                    "Minimum, maximum and out-of-range quantities",
                    "Medium",
                ),
                (
                    "Exception", "Handle payment processing failure",
                    "A cart is ready for checkout.",
                    "1. Submit a test order using an authorised test payment method.\n"
                    "2. Simulate or observe payment failure.",
                    "The order is not incorrectly marked as paid and the "
                    "user receives a clear outcome.",
                    "Payment provider test decline or simulated failure",
                    "High",
                ),
                (
                    "Alternate Path", "Update cart before placing an order",
                    "The cart contains at least one item.",
                    "1. Open the cart.\n"
                    "2. Change quantity or remove an item.\n"
                    "3. Continue to checkout.",
                    "The cart total and checkout details reflect the "
                    "latest cart contents.",
                    "Cart with multiple items",
                    "Medium",
                ),
            ]

        elif is_search:
            scenarios = [
                (
                    "Positive", "Search using a matching value",
                    "Searchable records exist.",
                    "1. Open the search page.\n"
                    "2. Enter a value known to match a record.\n"
                    "3. Submit the search.",
                    "Matching results are displayed accurately.",
                    "Existing search term",
                    "Medium",
                ),
                (
                    "Negative", "Search using a value with no matches",
                    "The search page is available.",
                    "1. Enter a value with no matching records.\n"
                    "2. Submit the search.",
                    "No matching results are shown and the page remains usable.",
                    "Unique non-matching search term",
                    "Low",
                ),
                (
                    "Boundary", "Search with empty or long input",
                    "The search page is available.",
                    "1. Submit an empty search.\n"
                    "2. Enter a long search string.\n"
                    "3. Observe validation and results.",
                    "Input limits and empty-input behaviour follow the "
                    "defined requirements.",
                    "Empty string; maximum-length input; over-length input",
                    "Medium",
                ),
                (
                    "Exception", "Handle a search service error",
                    "The search page is available.",
                    "1. Submit a valid search.\n"
                    "2. Simulate or observe a search service error.",
                    "The application displays a useful error state and "
                    "does not crash.",
                    "Valid search term; simulated service failure",
                    "Medium",
                ),
                (
                    "Alternate Path", "Refine results using filters or sorting",
                    "Search results are available.",
                    "1. Perform a search.\n"
                    "2. Apply a filter or sorting option.\n"
                    "3. Remove the filter or change the sort order.",
                    "The results update correctly and reflect the selected options.",
                    "Search term with several matching records",
                    "Low",
                ),
            ]

        else:
            scenarios = [
                (
                    "Positive", "Verify the required behaviour",
                    "The application is available and required test data exists.",
                    "1. Navigate to the relevant feature.\n"
                    "2. Perform the action described in the requirement.\n"
                    "3. Observe the result.",
                    "The application behaves as specified: " + text,
                    "Valid input and required preconditions",
                    "Medium",
                ),
                (
                    "Negative", "Verify handling of invalid input",
                    "The relevant feature is available.",
                    "1. Enter missing, invalid or unsupported data.\n"
                    "2. Submit or continue.\n"
                    "3. Observe the response.",
                    "Invalid input is handled according to the requirement "
                    "and no unintended action occurs.",
                    "Invalid value; missing required value",
                    "Medium",
                ),
                (
                    "Boundary", "Verify minimum and maximum values",
                    "Relevant input limits or business rules are defined.",
                    "1. Test the minimum permitted value.\n"
                    "2. Test the maximum permitted value.\n"
                    "3. Test a value just outside each boundary.",
                    "Boundary conditions are handled according to the "
                    "documented business rules.",
                    "Minimum; maximum; just below and above boundaries",
                    "Medium",
                ),
                (
                    "Exception", "Verify graceful handling of failure",
                    "The feature is available in a test environment.",
                    "1. Perform the action under test.\n"
                    "2. Simulate or observe an authorised service, network "
                    "or dependency failure.\n"
                    "3. Check the response.",
                    "The application handles the failure gracefully and "
                    "does not leave inconsistent data.",
                    "Valid test input; simulated dependency failure",
                    "High",
                ),
                (
                    "Alternate Path", "Verify an alternative user journey",
                    "The feature is available.",
                    "1. Start the normal user journey.\n"
                    "2. Use an available alternative, cancel or back action.\n"
                    "3. Resume or exit the journey.",
                    "The alternative path behaves correctly and preserves "
                    "data consistency.",
                    "Valid test input; alternative navigation choice",
                    "Low",
                ),
            ]

        for test_type, title, pre, steps, expected, data, priority in scenarios:
            if test_type in selected_types:
                cases.append(
                    make_test_case(
                        req_id=req_id,
                        title=title,
                        test_type=test_type,
                        precondition=pre,
                        steps=steps,
                        expected=expected,
                        test_data=data,
                        priority=priority,
                    )
                )

    for index, case in enumerate(cases, start=1):
        case["Test Case ID"] = f"TC-{index:04d}"

    return pd.DataFrame(cases)


# =========================================================
# 5. RISK ANALYSIS AGENT
# =========================================================

def risk_analyst_agent(requirements):
    rows = []

    for req in requirements:
        text = req["Requirement"]
        lower = text.lower()
        score = 0
        factors = []

        if contains_any(
            lower,
            ["payment", "transfer", "transaction", "funds", "money"],
        ):
            score += 3
            factors.append("Financial transaction")

        if contains_any(
            lower,
            ["password", "login", "authentication", "security", "access"],
        ):
            score += 3
            factors.append("Authentication or security")

        if contains_any(
            lower,
            ["delete", "remove", "cancel", "update", "change"],
        ):
            score += 1
            factors.append("Data modification")

        if contains_any(
            lower,
            ["personal", "private", "sensitive", "customer data"],
        ):
            score += 2
            factors.append("Potentially sensitive data")

        if len(text.split()) < 7:
            score += 1
            factors.append("Limited requirement detail")

        if score >= 4:
            level = "High"
            action = "Prioritise detailed negative, boundary and regression testing."
        elif score >= 2:
            level = "Medium"
            action = "Review test coverage and validate important alternate paths."
        else:
            level = "Low"
            action = "Validate core behaviour and confirm acceptance criteria."

        rows.append({
            "Requirement ID": req["Requirement ID"],
            "Requirement": text,
            "Risk Score": score,
            "Risk Level": level,
            "Risk Factors": ", ".join(factors) if factors else "No specific heuristic detected",
            "Recommended Action": action,
        })

    return pd.DataFrame(rows)


# =========================================================
# 6. DUPLICATE DETECTION AND COVERAGE GAP AGENTS
# =========================================================

def duplicate_detection_agent(test_cases):
    rows = []
    seen = {}

    for _, row in test_cases.iterrows():
        key = re.sub(
            r"[^a-z0-9]+", " ",
            clean_text(row["Test Scenario"]).lower(),
        ).strip()

        if key in seen:
            rows.append({
                "Test Case ID": row["Test Case ID"],
                "Similar To": seen[key],
                "Scenario": row["Test Scenario"],
                "Finding": "Potential exact or near-duplicate scenario.",
                "Recommendation": "Review whether the cases test distinct behaviour.",
            })
        else:
            seen[key] = row["Test Case ID"]

    return pd.DataFrame(
        rows,
        columns=[
            "Test Case ID", "Similar To", "Scenario",
            "Finding", "Recommendation",
        ],
    )


def coverage_gap_agent(requirements, test_cases):
    rows = []
    tested_ids = set(test_cases["Requirement ID"].astype(str))

    for req in requirements:
        req_id = req["Requirement ID"]

        if req_id not in tested_ids:
            rows.append({
                "Requirement ID": req_id,
                "Requirement": req["Requirement"],
                "Gap": "No test cases generated.",
                "Recommendation": "Create and review test scenarios.",
            })
            continue

        req_tests = test_cases[test_cases["Requirement ID"] == req_id]
        actual_types = set(req_tests["Test Type"].astype(str))
        missing = set(TEST_TYPES) - actual_types

        if missing:
            rows.append({
                "Requirement ID": req_id,
                "Requirement": req["Requirement"],
                "Gap": "Selected test categories not generated: "
                       + ", ".join(sorted(missing)),
                "Recommendation": "Review whether additional test types "
                                  "are required for this requirement.",
            })

    return pd.DataFrame(
        rows,
        columns=[
            "Requirement ID", "Requirement", "Gap", "Recommendation",
        ],
    )


# =========================================================
# 7. TRACEABILITY AND ACCEPTANCE CRITERIA
# =========================================================

def build_traceability(requirements, test_cases):
    rows = []

    for req in requirements:
        req_id = req["Requirement ID"]
        matching = test_cases[test_cases["Requirement ID"] == req_id]

        if matching.empty:
            rows.append({
                "Requirement ID": req_id,
                "Requirement": req["Requirement"],
                "Test Case IDs": "",
                "Test Case Count": 0,
                "Coverage Status": "Not Covered",
            })
        else:
            rows.append({
                "Requirement ID": req_id,
                "Requirement": req["Requirement"],
                "Test Case IDs": ", ".join(matching["Test Case ID"].astype(str)),
                "Test Case Count": len(matching),
                "Coverage Status": "Test Cases Generated",
            })

    return pd.DataFrame(rows)


def build_acceptance_criteria(requirements):
    rows = []

    for req in requirements:
        text = req["Requirement"]
        lower = text.lower()

        rows.append({
            "Requirement ID": req["Requirement ID"],
            "Requirement": text,
            "Suggested Acceptance Criteria": (
                f"Given the required preconditions for {req['Requirement ID']}, "
                f"when the user performs the action described in the requirement, "
                f"then the application should produce the expected business outcome."
            ),
            "Positive Criteria": "Valid inputs and permitted actions are processed correctly.",
            "Negative Criteria": "Invalid inputs and unauthorised actions are handled safely.",
            "Boundary Criteria": (
                "Applicable limits and boundary values are validated."
                if contains_any(lower, ["limit", "maximum", "minimum", "amount", "length", "quantity"])
                else "Confirm applicable boundaries with the product owner."
            ),
            "Review Required": "Yes — confirm measurable outcomes and business rules.",
        })

    return pd.DataFrame(rows)


# =========================================================
# 8. EXCEL EXPORT
# =========================================================

def create_excel(tables):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, dataframe in tables.items():
            dataframe.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
            )

        workbook = writer.book

        for worksheet in workbook.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions

            for cell in worksheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(
                    fill_type="solid",
                    fgColor="1F4E78",
                )
                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center",
                    wrap_text=True,
                )

            worksheet.row_dimensions[1].height = 32

            for column_cells in worksheet.columns:
                max_length = 0
                column_index = column_cells[0].column

                for cell in column_cells:
                    cell.alignment = Alignment(
                        vertical="top",
                        wrap_text=True,
                    )
                    value = "" if cell.value is None else str(cell.value)
                    max_length = max(
                        max_length,
                        min(len(value), 55),
                    )

                worksheet.column_dimensions[
                    get_column_letter(column_index)
                ].width = min(max(max_length + 3, 14), 45)

    output.seek(0)
    return output.getvalue()


# =========================================================
# 9. USER INPUT AND TEST GENERATION
# =========================================================

with st.sidebar:
    st.header("Generation Settings")

    demo_mode = st.toggle("Demo Mode", value=True, disabled=True)

    st.caption("Rule-based generation is active. No API key is needed.")

    selected_types = st.multiselect(
        "Test types to generate",
        options=TEST_TYPES,
        default=TEST_TYPES,
        help="Choose which scenario categories to include.",
    )

    st.caption(
        "Tip: Start with all five test types. "
        "You can narrow the output later."
    )


requirement_text = st.text_area(
    "Enter requirements — one requirement per line",
    height=170,
    placeholder=(
        "The user should be able to log in with valid credentials.\n"
        "The user should be able to transfer funds to a registered payee.\n"
        "The system should allow users to search transactions."
    ),
)

generate_clicked = st.button(
    "Generate Test Cases and QA Analysis",
    type="primary",
    use_container_width=True,
)

if generate_clicked:
    lines = [
        line.strip()
        for line in requirement_text.splitlines()
        if line.strip()
    ]

    if not lines:
        st.warning("Please enter at least one requirement.")
    elif not selected_types:
        st.warning("Select at least one test type.")
    else:
        requirements = [
            {
                "Requirement ID": f"REQ-{index:03d}",
                "Requirement": line,
            }
            for index, line in enumerate(lines, start=1)
        ]

        test_cases = test_designer_agent(requirements, selected_types)

        st.session_state["requirements"] = requirements
        st.session_state["test_cases"] = test_cases

        st.session_state["ambiguity"] = requirement_analyst_agent(requirements)
        st.session_state["risk"] = risk_analyst_agent(requirements)
        st.session_state["duplicates"] = duplicate_detection_agent(test_cases)
        st.session_state["gaps"] = coverage_gap_agent(requirements, test_cases)
        st.session_state["traceability"] = build_traceability(requirements, test_cases)
        st.session_state["acceptance"] = build_acceptance_criteria(requirements)

        st.success(
            f"Generated {len(test_cases)} test cases for "
            f"{len(requirements)} requirement(s)."
        )


# =========================================================
# 10. PROFESSIONAL QA DASHBOARD
# =========================================================

if "test_cases" not in st.session_state:
    st.info(
        "Enter one or more requirements above and select "
        "'Generate Test Cases and QA Analysis' to get started."
    )
    st.stop()


st.divider()
st.header("📊 QA Execution Dashboard")

test_cases = st.session_state["test_cases"].copy()

# Editable test results are retained in session state.
edited_cases = st.data_editor(
    test_cases,
    key="editable_test_cases",
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Requirement ID": st.column_config.TextColumn(disabled=True),
        "Test Case ID": st.column_config.TextColumn(disabled=True),
        "Test Scenario": st.column_config.TextColumn(),
        "Test Type": st.column_config.SelectboxColumn(options=TEST_TYPES),
        "Priority": st.column_config.SelectboxColumn(options=PRIORITIES),
        "Status": st.column_config.SelectboxColumn(options=EXECUTION_STATUSES),
        "Preconditions": st.column_config.TextColumn(),
        "Test Steps": st.column_config.TextColumn(),
        "Test Data": st.column_config.TextColumn(),
        "Expected Result": st.column_config.TextColumn(),
        "Actual Result": st.column_config.TextColumn(),
        "Defect ID": st.column_config.TextColumn(),
    },
)

st.session_state["test_cases"] = edited_cases

total = len(edited_cases)
passed = int((edited_cases["Status"] == "Pass").sum())
failed = int((edited_cases["Status"] == "Fail").sum())
blocked = int((edited_cases["Status"] == "Blocked").sum())
not_run = int((edited_cases["Status"] == "Not Run").sum())
executed = passed + failed + blocked

pass_rate = (passed / executed * 100) if executed else 0
execution_rate = (executed / total * 100) if total else 0

metric_cols = st.columns(4)
metric_cols[0].metric("Total Test Cases", total)
metric_cols[1].metric("Passed", passed)
metric_cols[2].metric("Failed", failed)
metric_cols[3].metric("Blocked", blocked)

metric_cols = st.columns(4)
metric_cols[0].metric("Not Run", not_run)
metric_cols[1].metric("Execution Rate", f"{execution_rate:.1f}%")
metric_cols[2].metric("Pass Rate", f"{pass_rate:.1f}%")
metric_cols[3].metric(
    "Requirements",
    len(st.session_state["requirements"]),
)

st.subheader("Execution Progress")
st.progress(execution_rate / 100 if total else 0)

if total:
    chart_data = pd.DataFrame({
        "Status": ["Pass", "Fail", "Blocked", "Not Run"],
        "Count": [passed, failed, blocked, not_run],
    }).set_index("Status")

    st.bar_chart(chart_data)


# =========================================================
# 11. SEARCH AND FILTER
# =========================================================

st.divider()
st.subheader("🔎 Search and Filter Test Cases")

filter_cols = st.columns(4)

search_text = filter_cols[0].text_input(
    "Search scenario or requirement",
)

priority_filter = filter_cols[1].selectbox(
    "Priority",
    ["All"] + PRIORITIES,
)

type_filter = filter_cols[2].selectbox(
    "Test Type",
    ["All"] + TEST_TYPES,
)

status_filter = filter_cols[3].selectbox(
    "Execution Status",
    ["All"] + EXECUTION_STATUSES,
)

filtered = edited_cases.copy()

if search_text:
    mask = (
        filtered["Test Scenario"].astype(str).str.contains(
            search_text, case=False, na=False
        )
        | filtered["Requirement ID"].astype(str).str.contains(
            search_text, case=False, na=False
        )
        | filtered["Test Case ID"].astype(str).str.contains(
            search_text, case=False, na=False
        )
    )
    filtered = filtered[mask]

if priority_filter != "All":
    filtered = filtered[filtered["Priority"] == priority_filter]

if type_filter != "All":
    filtered = filtered[filtered["Test Type"] == type_filter]

if status_filter != "All":
    filtered = filtered[filtered["Status"] == status_filter]

st.caption(f"Showing {len(filtered)} of {len(edited_cases)} test cases.")
st.dataframe(filtered, use_container_width=True, hide_index=True)


# =========================================================
# 12. ANALYSIS TABS
# =========================================================

st.divider()
st.header("🤖 Agent Analysis Results")

tabs = st.tabs([
    "Requirement Analysis",
    "Risk Analysis",
    "Coverage Gaps",
    "Traceability",
    "Acceptance Criteria",
    "Duplicate Detection",
])

with tabs[0]:
    st.subheader("Potential Ambiguities")
    st.dataframe(
        st.session_state["ambiguity"],
        use_container_width=True,
        hide_index=True,
    )

with tabs[1]:
    st.subheader("Requirement Risk Assessment")
    risk_df = st.session_state["risk"]
    st.dataframe(risk_df, use_container_width=True, hide_index=True)

    high_risk = int((risk_df["Risk Level"] == "High").sum())
    medium_risk = int((risk_df["Risk Level"] == "Medium").sum())
    low_risk = int((risk_df["Risk Level"] == "Low").sum())

    rcols = st.columns(3)
    rcols[0].metric("High Risk", high_risk)
    rcols[1].metric("Medium Risk", medium_risk)
    rcols[2].metric("Low Risk", low_risk)

with tabs[2]:
    st.subheader("Potential Coverage Gaps")
    st.dataframe(
        coverage_gap_agent(
            st.session_state["requirements"],
            edited_cases,
        ),
        use_container_width=True,
        hide_index=True,
    )

with tabs[3]:
    st.subheader("Requirement Traceability Matrix")
    st.dataframe(
        build_traceability(
            st.session_state["requirements"],
            edited_cases,
        ),
        use_container_width=True,
        hide_index=True,
    )

with tabs[4]:
    st.subheader("Suggested Acceptance Criteria")
    st.dataframe(
        st.session_state["acceptance"],
        use_container_width=True,
        hide_index=True,
    )

with tabs[5]:
    st.subheader("Potential Duplicate Scenarios")
    st.dataframe(
        duplicate_detection_agent(edited_cases),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# 13. EXPORT ALL RESULTS TO EXCEL
# =========================================================

st.divider()
st.header("📥 Export QA Report")

current_requirements = pd.DataFrame(st.session_state["requirements"])
current_ambiguity = requirement_analyst_agent(
    st.session_state["requirements"]
)
current_risk = risk_analyst_agent(
    st.session_state["requirements"]
)
current_gaps = coverage_gap_agent(
    st.session_state["requirements"],
    edited_cases,
)
current_traceability = build_traceability(
    st.session_state["requirements"],
    edited_cases,
)
current_acceptance = st.session_state["acceptance"]
current_duplicates = duplicate_detection_agent(edited_cases)

excel_tables = {
    "Test Cases": edited_cases,
    "Coverage & Gaps": current_gaps,
    "Requirement Traceability Matrix": current_traceability,
    "Acceptance Criteria": current_acceptance,
    "Risk Analysis": current_risk,
    "Duplicate Detection": current_duplicates,
    "Ambiguity Analysis": current_ambiguity,
}

excel_bytes = create_excel(excel_tables)

st.download_button(
    label="⬇️ Download Complete QA Report (Excel)",
    data=excel_bytes,
    file_name="Multi_Agent_AI_Test_Assistant_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
    use_container_width=True,
)

st.caption(
    "Note: Analysis is heuristic and rule-based in Demo Mode. "
    "Review scenarios, risks, acceptance criteria and execution results "
    "against the actual requirements before using them for release decisions."
)
