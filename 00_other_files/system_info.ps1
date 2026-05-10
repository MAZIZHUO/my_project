# ========================================
# 系统信息查询脚本
# ========================================

$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "           系统基本信息" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 操作系统信息
Write-Host "`n[操作系统]" -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "系统名称：$($os.Caption)"
Write-Host "系统版本：$($os.Version)"
Write-Host "系统架构：$($os.OSArchitecture)"
Write-Host "最后启动：$($os.LastBootUpTime)"

# 计算机名和用户
Write-Host "`n[用户信息]" -ForegroundColor Yellow
Write-Host "计算机名：$($env:COMPUTERNAME)"
Write-Host "当前用户：$($env:USERNAME)"
Write-Host "用户目录：$($env:USERPROFILE)"

# CPU 信息
Write-Host "`n[CPU 信息]" -ForegroundColor Yellow
$cpu = Get-CimInstance Win32_Processor
Write-Host "处理器：$($cpu.Name)"
Write-Host "核心数：$($cpu.NumberOfCores)"
Write-Host "逻辑处理器：$($cpu.NumberOfLogicalProcessors)"

# 内存信息
Write-Host "`n[内存信息]" -ForegroundColor Yellow
$totalRAM = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
$freeRAM = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
$usedRAM = [math]::Round($totalRAM - $freeRAM, 2)
Write-Host "总内存：$($totalRAM) GB"
Write-Host "已使用：$($usedRAM) GB"
Write-Host "剩余：$($freeRAM) GB"

# 磁盘信息
Write-Host "`n[磁盘信息]" -ForegroundColor Yellow
$disks = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3"
foreach ($disk in $disks) {
    $total = [math]::Round($disk.Size / 1GB, 2)
    $free = [math]::Round($disk.FreeSpace / 1GB, 2)
    $used = [math]::Round($total - $free, 2)
    Write-Host "磁盘 $($disk.DeviceID)  总共：$($total) GB  已用：$($used) GB  剩余：$($free) GB"
}

# 网络信息
Write-Host "`n[网络信息]" -ForegroundColor Yellow
$adapters = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne "127.0.0.1" }
foreach ($adapter in $adapters) {
    Write-Host "接口：$($adapter.InterfaceAlias)  IP：$($adapter.IPAddress)"
}

# Python 环境
Write-Host "`n[Python 环境]" -ForegroundColor Yellow
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "Python 版本：$pythonVersion"
    $pipVersion = & pip --version 2>&1
    Write-Host "pip 版本：$pipVersion"
}
catch {
    Write-Host "未检测到 Python" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "           查询完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
