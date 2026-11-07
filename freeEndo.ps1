param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PythonArguments
)

$signature = @'
using System;
using System.Runtime.InteropServices;

public static class EndoPowerManagement
{
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint executionState);
}
'@

Add-Type -TypeDefinition $signature

$ES_CONTINUOUS = [uint32]2147483648
$ES_SYSTEM_REQUIRED = [uint32]1
$executionState = $ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED
$previousState = [EndoPowerManagement]::SetThreadExecutionState($executionState)

if ($previousState -eq 0) {
    throw "Windows could not enable the temporary sleep prevention request."
}

$exitCode = 1
try {
    $mainScript = Join-Path $PSScriptRoot "main.py"
    & py -3 $mainScript @PythonArguments
    $exitCode = $LASTEXITCODE
}
finally {
    [void][EndoPowerManagement]::SetThreadExecutionState($ES_CONTINUOUS)
}

exit $exitCode
