"""Generates HospitalAPI.jmx (JMeter 5.x test plan). Run: python build_jmx.py"""
from xml.sax.saxutils import escape as esc

def s(name, val): return f'<stringProp name="{name}">{esc(str(val))}</stringProp>'
def b(name, val): return f'<boolProp name="{name}">{str(val).lower()}</boolProp>'
def tree(inner=""): return f"<hashTree>{inner}</hashTree>"

def sampler(name, method, path, body=None):
    args = ""
    if body is not None:
        args = ('<elementProp name="HTTPsampler.Arguments" elementType="Arguments"><collectionProp name="Arguments.arguments">'
                '<elementProp name="" elementType="HTTPArgument">' + b("HTTPArgument.always_encode", False) +
                s("Argument.value", body) + s("Argument.metadata", "=") + b("HTTPArgument.use_equals", True) +
                '</elementProp></collectionProp></elementProp>')
    else:
        args = '<elementProp name="HTTPsampler.Arguments" elementType="Arguments"><collectionProp name="Arguments.arguments"/></elementProp>'
    return (f'<HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="{esc(name)}" enabled="true">'
            + args + b("HTTPSampler.postBodyRaw", body is not None) + s("HTTPSampler.path", path)
            + s("HTTPSampler.method", method) + b("HTTPSampler.follow_redirects", True)
            + b("HTTPSampler.use_keepalive", True) + '</HTTPSamplerProxy>')

def code_assert(expected, name="Assert response code"):
    return (f'<ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion" testname="{esc(name)}" enabled="true">'
            '<collectionProp name="Asserion.test_strings">' + f'<stringProp name="1">{esc(expected)}</stringProp>' + '</collectionProp>'
            + s("Assertion.custom_message", "") + s("Assertion.test_field", "Assertion.response_code")
            + b("Assertion.assume_success", False) + '<intProp name="Assertion.test_type">8</intProp></ResponseAssertion>')

def json_assert(path, value, name):
    return (f'<JSONPathAssertion guiclass="JSONPathAssertionGui" testclass="JSONPathAssertion" testname="{esc(name)}" enabled="true">'
            + s("JSON_PATH", path) + s("EXPECTED_VALUE", value) + b("JSONVALIDATION", True)
            + b("EXPECT_NULL", False) + b("INVERT", False) + b("ISREGEX", False) + '</JSONPathAssertion>')

def extractor(var, path):
    return (f'<JSONPostProcessor guiclass="JSONPostProcessorGui" testclass="JSONPostProcessor" testname="Extract {var}" enabled="true">'
            + s("JSONPostProcessor.referenceNames", var) + s("JSONPostProcessor.jsonPathExprs", path)
            + s("JSONPostProcessor.match_numbers", "1") + s("JSONPostProcessor.defaultValues", "NOT_FOUND") + '</JSONPostProcessor>')

def duration_assert(ms):
    return (f'<DurationAssertion guiclass="DurationAssertionGui" testclass="DurationAssertion" testname="Response time under {ms} ms" enabled="true">'
            + s("DurationAssertion.duration", ms) + '</DurationAssertion>')

def sampler_node(name, method, path, body, expected, extra=""):
    return sampler(name, method, path, body) + tree(code_assert(expected) + tree() + duration_assert(2000) + tree() + extra)

def thread_group(name, loops, inner, stop_on_eof=False, setup=False):
    tag = "SetupThreadGroup" if setup else "ThreadGroup"
    gui = "SetupThreadGroupGui" if setup else "ThreadGroupGui"
    return (f'<{tag} guiclass="{gui}" testclass="{tag}" testname="{esc(name)}" enabled="true">'
            + s("ThreadGroup.on_sample_error", "continue")
            + '<elementProp name="ThreadGroup.main_controller" elementType="LoopController" guiclass="LoopControlPanel" testclass="LoopController" testname="Loop Controller" enabled="true">'
            + b("LoopController.continue_forever", False) + s("LoopController.loops", loops) + '</elementProp>'
            + s("ThreadGroup.num_threads", 1) + s("ThreadGroup.ramp_time", 1)
            + b("ThreadGroup.scheduler", False) + f'</{tag}>' + tree(inner))

HDR = ('<HeaderManager guiclass="HeaderPanel" testclass="HeaderManager" testname="HTTP Header Manager" enabled="true">'
       '<collectionProp name="HeaderManager.headers"><elementProp name="" elementType="Header">'
       + s("Header.name", "Content-Type") + s("Header.value", "application/json") +
       '</elementProp></collectionProp></HeaderManager>' + tree())

DEFAULTS = ('<ConfigTestElement guiclass="HttpDefaultsGui" testclass="ConfigTestElement" testname="HTTP Request Defaults" enabled="true">'
            '<elementProp name="HTTPsampler.Arguments" elementType="Arguments" guiclass="HTTPArgumentsPanel" testclass="Arguments" testname="User Defined Variables" enabled="true">'
            '<collectionProp name="Arguments.arguments"/></elementProp>'
            + s("HTTPSampler.domain", "${HOST}") + s("HTTPSampler.port", "${PORT}") + s("HTTPSampler.protocol", "http")
            + '</ConfigTestElement>' + tree())

def var_row(n, v):
    return ('<elementProp name="%s" elementType="Argument">' % n + s("Argument.name", n) + s("Argument.value", v)
            + s("Argument.metadata", "=") + '</elementProp>')

USERVARS = ('<Arguments guiclass="ArgumentsPanel" testclass="Arguments" testname="User Defined Variables" enabled="true">'
            '<collectionProp name="Arguments.arguments">'
            + var_row("HOST", "${__P(host,localhost)}") + var_row("PORT", "${__P(port,5000)}")
            + var_row("FUTURE_DATE", "${__timeShift(yyyy-MM-dd,,P30D,,)}") + var_row("PAST_DATE", "2020-01-01")
            + '</collectionProp></Arguments>' + tree())

CSV = ('<CSVDataSet guiclass="TestBeanGUI" testclass="CSVDataSet" testname="CSV Data Set Config (patients.csv)" enabled="true">'
       + s("filename", "patients.csv") + s("fileEncoding", "UTF-8")
       + s("variableNames", "tcid,scenario,name,age,phone,email,expected") + b("ignoreFirstLine", True)
       + s("delimiter", ",") + b("quotedData", False) + b("recycle", False) + b("stopThread", True)
       + s("shareMode", "shareMode.all") + '</CSVDataSet>' + tree())

def listener(gui, name, cls="ResultCollector"):
    return (f'<ResultCollector guiclass="{gui}" testclass="ResultCollector" testname="{name}" enabled="true">'
            + b("ResultCollector.error_logging", False) + '</ResultCollector>' + tree())

# ---- setUp: reset in-memory DB so reruns are repeatable
setup = thread_group("setUp - Reset DB", 1, sampler_node("Reset database", "POST", "/reset", "{}", "200"), setup=True)

# ---- Patient registration (data-driven TC01-TC08)
pat_body = '{"name":"${name}","age":${age},"phone":"${phone}","email":"${email}"}'
pat_sampler = sampler_node("${tcid} ${scenario}", "POST", "/patients", pat_body, "${expected}",
                           extractor("patientId", "$.id") + tree())
patients_tg = thread_group("Patient Registration (CSV-driven)", -1, CSV + HDR + pat_sampler, stop_on_eof=True)

# ---- Appointments and records (TC09-TC14)
reg_body = '{"name":"Flow Patient","age":40,"phone":"9123456780","email":"flow_${__UUID()}@x.com"}'
flow = (HDR
  + sampler_node("Setup: register patient", "POST", "/patients", reg_body, "201", extractor("flowPatientId", "$.id") + tree())
  + sampler_node("TC09 Book valid appointment", "POST", "/appointments",
      '{"patientId":${flowPatientId},"doctor":"Dr. Rao","date":"${FUTURE_DATE}","time":"10:30"}', "201",
      extractor("appointmentId", "$.id") + tree() + json_assert("$.doctor", "Dr. Rao", "Doctor name echoed") + tree())
  + sampler_node("TC10 Appointment unknown patient", "POST", "/appointments",
      '{"patientId":9999,"doctor":"Dr. Rao","date":"${FUTURE_DATE}","time":"11:00"}', "404")
  + sampler_node("TC11 Past-date appointment", "POST", "/appointments",
      '{"patientId":${flowPatientId},"doctor":"Dr. Rao","date":"${PAST_DATE}","time":"11:00"}', "400")
  + sampler_node("TC12 Double-book same slot", "POST", "/appointments",
      '{"patientId":${flowPatientId},"doctor":"Dr. Rao","date":"${FUTURE_DATE}","time":"10:30"}', "409")
  + sampler_node("TC13 Add medical record", "POST", "/records",
      '{"patientId":${flowPatientId},"diagnosis":"Hypertension","notes":"Review in 2 weeks"}', "201")
  + sampler_node("TC14 Records for unknown patient", "GET", "/records/9999", None, "404")
  + sampler_node("Extra: fetch records for patient", "GET", "/records/${flowPatientId}", None, "200",
      json_assert("$[0].diagnosis", "Hypertension", "Diagnosis returned") + tree())
  + sampler_node("Extra: delete appointment", "DELETE", "/appointments/${appointmentId}", None, "200"))
flow_tg = thread_group("Appointments and Records Flow", 1, flow)

listeners = (listener("ViewResultsFullVisualizer", "View Results Tree") + listener("SummaryReport", "Summary Report")
             + listener("StatVisualizer", "Aggregate Report"))

plan = ('<?xml version="1.0" encoding="UTF-8"?><jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6.3"><hashTree>'
        '<TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Hospital Management API Test Plan" enabled="true">'
        + b("TestPlan.functional_mode", False) + b("TestPlan.serialize_threadgroups", True)
        + '<elementProp name="TestPlan.user_defined_variables" elementType="Arguments" guiclass="ArgumentsPanel" testclass="Arguments" testname="User Defined Variables" enabled="true"><collectionProp name="Arguments.arguments"/></elementProp>'
        + '</TestPlan>' + tree(USERVARS + DEFAULTS + setup + patients_tg + flow_tg + listeners) + '</hashTree></jmeterTestPlan>')

open("HospitalAPI.jmx", "w", encoding="utf-8").write(plan)
print("HospitalAPI.jmx written,", len(plan), "bytes")
