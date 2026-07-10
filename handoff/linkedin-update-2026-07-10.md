# LinkedIn Update — Regress-Guard (post as a new post OR a comment on the original)

> The original announcement is already live. This is a short **progress update** — you post it
> (a new post, or a comment under the first one). Keep the same hashtags.

---

**Update on Regress-Guard — I spent the week making the claims impossible to argue with.** 🧠

Regress-Guard is a memory for AI coding agents whose confidence is *earned from real test outcomes* — not the model's opinion — and that **forgets what a refactor made wrong**.

Since the launch I focused on one thing: **proof, honestly reported.**

🔬 **External benchmark** — on LongMemEval (`knowledge-update`), memory lifts QA from a **5% floor to ~82%**. Honest scope stated (oracle split; a recency-ablation arm showed *no* lift — reported as a null, not hidden).

📉 **The forgetting, measured** — a poison-demotion curve watches a plausible-but-wrong lesson lose confidence on every real `pytest` failure, drop below the injection gate after the *first* fail, and get tombstoned after 0/6 — across **all 5 bug classes**.

🎯 **Does the confidence number mean anything?** — a non-circular transfer test grounds confidence on a *seen* task and measures it on an *unseen* variant. It separates signal from noise — **and surfaces a real miss** (one lesson claimed 0.9 but transferred 0/8). We report the limit, not just the win.

🕐 **Bi-temporal time-travel** — a slider scrubs the 3D knowledge globe through its own history; drag it back and a since-forgotten lesson reappears exactly as it was *valid then*.

Everything is reproducible, **119/119 tests green**, live on Alibaba Cloud, and open source.

The through-line: in an era where every AI demo overclaims, **radical honesty is the moat** — I show the failures too.

Built for the Global AI Hackathon with **Qwen Cloud**. 🚀

#QwenCloud #AlibabaCloud #MemoryAgent #AI #OpenSource #MachineLearning
