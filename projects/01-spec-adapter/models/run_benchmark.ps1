$Tests = @(
    @{
        Id          = "Test 1: Parametric Compressor Sizing"
        Instruction = "Select the appropriate Copeland compressor model matching the required cooling capacity, refrigerant specification, and electrical supply. Return performance metrics in structured JSON."
        Input       = "Design Requirements: Capacity Target = ~147,000 BTU/hr | Refrigerant = R-454B | Application = Air Conditioning | Electrical = 460/380-420 V, 3 Ph, 50/60 Hz"
    },
    @{
        Id          = "Test 2: Electrical Protection Sizing"
        Instruction = "Calculate electrical safety metrics and circuit protection requirements for the specified compressor model. Provide contactor rating, breaker rating (MOCP), and LRA constraints."
        Input       = "Compressor Model: YA147K1E-TFD-ERZ | Electrical System: 460/380-420 V, 3-Phase, 50/60 Hz"
    },
    @{
        Id          = "Test 3: Nomenclature Parsing"
        Instruction = "Deconstruct the Copeland compressor model number into engineering specifications. Extract series, capacity multiplier, electrical code, and protection configuration."
        Input       = "Compressor Model: ZP54K5E-TF5-830"
    }
)

function Test-OllamaModel {
    param([string]$ModelName)

    Write-Host "`n========================================================" -ForegroundColor Cyan
    Write-Host " RUNNING BENCHMARK FOR: $ModelName" -ForegroundColor Cyan
    Write-Host "========================================================" -ForegroundColor Cyan

    for ($i = 0; $i -lt $Tests.Count; $i++) {
        $t = $Tests[$i]
        Write-Host "`n[$($t.Id)]" -ForegroundColor Yellow
        Write-Host "Input: $($t.Input)" -ForegroundColor Gray

        $payload = @{
            model    = $ModelName
            stream   = $false
            options  = @{
                temperature = 0.1
                num_ctx     = 2048
            }
            messages = @(
                @{
                    role    = "user"
                    content = "$($t.Instruction)`n$($t.Input)"
                }
            )
        } | ConvertTo-Json -Depth 6

        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $resp = Invoke-RestMethod -Uri "http://localhost:11434/api/chat" -Method Post -Body $payload -ContentType "application/json"
            $sw.Stop()

            $text = $resp.message.content.Trim()
            $isValid = $true
            try { 
                $null = ConvertFrom-Json $text -ErrorAction Stop 
            } catch { 
                $isValid = $false 
            }

            $sec = [math]::Round($sw.Elapsed.TotalSeconds, 2)
            $status = if ($isValid) { "[PASS: Strict JSON]" } else { "[FAIL: Conversational/Markdown]" }
            $color = if ($isValid) { "Green" } else { "Red" }

            Write-Host "Latency: ${sec}s | Schema: " -NoNewline -ForegroundColor White
            Write-Host "$status" -ForegroundColor $color
            Write-Host $text -ForegroundColor Gray
        } catch {
            Write-Host "Inference Error on $ModelName`: $_" -ForegroundColor Red
        }
    }
}

Test-OllamaModel -ModelName "qwen-base"
Test-OllamaModel -ModelName "spec-adapter"