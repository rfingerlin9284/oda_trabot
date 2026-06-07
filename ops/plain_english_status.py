from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from oda_trabot import PHASE1_CONTRACT, SessionRouter


def main() -> None:
    router = SessionRouter(PHASE1_CONTRACT)
    now_et = datetime.now(ZoneInfo("America/New_York"))
    decision = router.route(now_et)

    print("ODA_TRABOT PHASE 1 STATUS")
    print()
    print(f"Time: {decision.current_time_et:%Y-%m-%d %I:%M:%S %p ET}")
    print(f"Detected session: {decision.detected_session.value}")
    print(f"Trading window open: {'YES' if decision.trading_window_open else 'NO'}")
    print(f"Session enabled: {'YES' if decision.session_enabled else 'NO'}")
    print(f"Can trade now: {'YES' if decision.can_trade else 'NO'}")
    print()
    print("Allowed pairs right now:")
    if decision.allowed_pairs:
        for pair in decision.allowed_pairs:
            print(f"- {pair}")
    else:
        print("- none")
    print()
    print("Allowed workflows right now:")
    if decision.active_workflows:
        for workflow in decision.active_workflows:
            print(f"- {workflow}")
    else:
        print("- none")


if __name__ == "__main__":
    main()
