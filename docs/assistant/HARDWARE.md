# Confirmed hardware and resource plan

| Part | Server | Gaming PC |
|---|---|---|
| CPU | Intel i7-10700K | Ryzen 9 7900X, 12 cores / 24 threads |
| RAM | 96 GB DDR4 | Crucial Pro 32 GB DDR5, 2x16 GB, CL36 6000 MHz |
| Motherboard | TUF GAMING Z490-PLUS | GIGABYTE B650 AORUS Elite AX |
| OS | Windows 11 Home | Windows 11, edition unspecified |
| Dedicated GPU | None | GIGABYTE RTX 3080 Ti Gaming OC 12G, 12 GB VRAM |
| PSU | Not specified | Thermaltake GF1 850 W, 80 Plus Gold |
| Free storage | Must measure | Must measure |

Only one dedicated GPU exists. Older notes about a planned server GPU are superseded. Tailscale
connects separate computers; it does not pool their RAM or VRAM.

Server owns the UI, controller, vault, search index, task database, reports and cloud sessions.
The gaming PC handles heavier local inference, Godot rendering and sequential asset generation.
High server RAM does not make large CPU model inference fast. Start with small models and measure.

The new controller runs one worker call at a time. Cloud planning/review is intermittent; genuine
concurrent cloud reasoning and local production, and a unified media/GPU lease scheduler, remain
explicit next integration work. Existing separate media processes must not compete for VRAM.

Before unattended use record: free disk, sleep/hibernation behavior, login startup, driver version,
Ollama version, CPU latency, peak VRAM at chosen context, gaming-mode pause, tunnel restart, network
loss, disk-full response and reboot recovery. Do not claim those checks passed without device access.
