import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import time
import random
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="💼 Job Market Signaling Game")

st.title("💼 Job Market Signaling Game")

# Firebase credentials and config
try:
    database_url = st.secrets["database_url"]

    service_account = {
        "type": st.secrets["type"],
        "project_id": st.secrets["project_id"],
        "private_key_id": st.secrets["private_key_id"],
        "private_key": st.secrets["private_key"],
        "client_email": st.secrets["client_email"],
        "client_id": st.secrets["client_id"],
        "auth_uri": st.secrets["auth_uri"],
        "token_uri": st.secrets["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["client_x509_cert_url"],
        "universe_domain": st.secrets["universe_domain"],
    }

    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account)
        firebase_admin.initialize_app(cred, {"databaseURL": database_url})

except KeyError:
    st.error("🔥 Firebase secrets not configured.")
    st.stop()

GAME_PREFIX = "job_market"
PLAYERS_REF = f"{GAME_PREFIX}_players"
MATCHES_REF = f"{GAME_PREFIX}_matches"
EXPECTED_REF = f"{GAME_PREFIX}_expected_players"

# Payoff helper
# Nature: High = 1/3, Low = 2/3
# Worker action: Effort / No Effort
# Firm action after Effort: Manager / Clerk
# Payoffs are (Worker, Firm)
def compute_payoffs(worker_type: str, worker_action: str, firm_action: str):
    if worker_action == "No Effort":
        return 4, 4

    if worker_type == "High":
        if firm_action == "Manager":
            return 6, 10
        return 0, 4

    # Low type with Effort
    if firm_action == "Manager":
        return 3, 0
    return -3, 4


def plot_enhanced_percentage_bar(choices, labels, title, player_type):
    if len(choices) > 0:
        counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0) * 100

        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('#f0f0f0')
        ax.set_facecolor('#e0e0e0')

        colors_scheme = ['#2ecc71', '#f39c12'] if player_type == "Worker" else ['#3498db', '#9b59b6']
        counts.plot(kind='bar', ax=ax, color=colors_scheme, linewidth=2, width=0.7)

        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel("Percentage (%)", fontsize=14)
        ax.set_xlabel("Choice", fontsize=14)
        ax.tick_params(rotation=0, labelsize=12)
        ax.set_ylim(0, max(100, counts.max() * 1.1))
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)

        for bar in ax.patches:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')

        ax.text(0.02, 0.98, f"Sample size: {len(choices)} participants",
                transform=ax.transAxes, fontsize=10, verticalalignment='top', alpha=0.7,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

        today = datetime.today().strftime('%B %d, %Y')
        ax.text(0.98, 0.98, f"Generated: {today}", transform=ax.transAxes,
                fontsize=10, verticalalignment='top', horizontalalignment='right', alpha=0.7)

        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.warning(f"⚠ No data available for {title}")


def create_pdf_report():
    """Create a PDF report from completed job-market matches."""
    from matplotlib.backends.backend_pdf import PdfPages
    import tempfile
    import os

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')

    with PdfPages(temp_file.name) as pdf:
        all_matches = db.reference(MATCHES_REF).get() or {}
        results_data = []

        for match_id, match_data in all_matches.items():
            if not isinstance(match_data, dict):
                continue
            if all(k in match_data for k in ["worker_action", "firm_action", "worker_type"]):
                worker_type = match_data["worker_type"]
                worker_action = match_data["worker_action"]
                firm_action = match_data["firm_action"]
                worker_payoff, firm_payoff = compute_payoffs(worker_type, worker_action, firm_action)

                results_data.append({
                    "Match_ID": match_id,
                    "Worker_Player": match_data.get("worker_player", ""),
                    "Firm_Player": match_data.get("firm_player", ""),
                    "Worker_Type": worker_type,
                    "Worker_Action": worker_action,
                    "Firm_Action": firm_action,
                    "Worker_Payoff": worker_payoff,
                    "Firm_Payoff": firm_payoff,
                })

        if results_data:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Job Market Signaling Game - Complete Results', fontsize=20, fontweight='bold')

            worker_actions = [r["Worker_Action"] for r in results_data]
            firm_actions = [r["Firm_Action"] for r in results_data]
            worker_types = [r["Worker_Type"] for r in results_data]

            action_counts = pd.Series(worker_actions).value_counts(normalize=True) * 100
            ax1.bar(action_counts.index, action_counts.values, alpha=0.8)
            ax1.set_title('Worker Actions')
            ax1.set_ylabel('Percentage (%)')
            for i, v in enumerate(action_counts.values):
                ax1.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
            ax1.grid(True, alpha=0.3)

            firm_counts = pd.Series(firm_actions).value_counts(normalize=True) * 100
            ax2.bar(firm_counts.index, firm_counts.values, alpha=0.8)
            ax2.set_title('Firm Responses')
            ax2.set_ylabel('Percentage (%)')
            for i, v in enumerate(firm_counts.values):
                ax2.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
            ax2.grid(True, alpha=0.3)

            type_counts = pd.Series(worker_types).value_counts(normalize=True) * 100
            ax3.bar(type_counts.index, type_counts.values, alpha=0.8)
            ax3.set_title('Worker Type Distribution')
            ax3.set_ylabel('Percentage (%)')
            for i, v in enumerate(type_counts.values):
                ax3.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
            ax3.grid(True, alpha=0.3)

            strategies = []
            for r in results_data:
                if r["Worker_Action"] == "No Effort":
                    strategies.append("Pooling")
                else:
                    strategies.append("Effort Signal")

            strategy_counts = pd.Series(strategies).value_counts(normalize=True) * 100
            ax4.bar(strategy_counts.index, strategy_counts.values, alpha=0.8)
            ax4.set_title('Strategy Analysis')
            ax4.set_ylabel('Percentage (%)')
            for i, v in enumerate(strategy_counts.values):
                ax4.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
            ax4.grid(True, alpha=0.3)

            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight', dpi=300)
            plt.close(fig)

            fig, ax = plt.subplots(figsize=(16, 10))
            ax.axis('tight')
            ax.axis('off')

            table_data = [["Match ID", "Worker", "Firm", "Type", "Worker Action", "Firm Action", "Worker Payoff", "Firm Payoff"]]
            for r in results_data:
                table_data.append([
                    r["Match_ID"], r["Worker_Player"], r["Firm_Player"], r["Worker_Type"],
                    r["Worker_Action"], r["Firm_Action"], str(r["Worker_Payoff"]), str(r["Firm_Payoff"])
                ])

            table = ax.table(cellText=table_data[1:], colLabels=table_data[0],
                             cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 2)

            for i in range(len(table_data[0])):
                table[(0, i)].set_facecolor('#4472C4')
                table[(0, i)].set_text_props(weight='bold', color='white')

            ax.set_title('Detailed Game Results', fontsize=16, fontweight='bold', pad=20)
            pdf.savefig(fig, bbox_inches='tight', dpi=300)
            plt.close(fig)

    with open(temp_file.name, 'rb') as f:
        pdf_content = f.read()

    os.unlink(temp_file.name)
    return pdf_content

# --- PLAYER REGISTRATION ---

st.header("👤 Join the Game")

player_name = st.text_input("Enter your name")

if st.button("Join Game"):
    if player_name.strip() == "":
        st.warning("Please enter a name.")
    else:
        players_ref = db.reference(PLAYERS_REF)
        players = players_ref.get() or {}

        if player_name in players:
            st.warning("Name already taken.")
        else:
            players_ref.child(player_name).set({
                "matched": False,
                "role": None,
                "match_id": None
            })
            st.success(f"Welcome, {player_name}!")
            st.rerun()


# --- MATCHING LOGIC ---

st.header("🔗 Matching")

players_ref = db.reference(PLAYERS_REF)
players = players_ref.get() or {}

unmatched_players = [p for p, data in players.items() if not data.get("matched")]

if st.button("Match Players"):
    if len(unmatched_players) < 2:
        st.warning("Not enough players to match.")
    else:
        random.shuffle(unmatched_players)

        for i in range(0, len(unmatched_players) - 1, 2):
            p1 = unmatched_players[i]
            p2 = unmatched_players[i + 1]

            match_id = f"match_{int(time.time())}_{i}"

            # Randomly assign roles
            if random.random() < 0.5:
                worker, firm = p1, p2
            else:
                worker, firm = p2, p1

            # Nature draw (High = 1/3, Low = 2/3)
            worker_type = "High" if random.random() < (1/3) else "Low"

            db.reference(MATCHES_REF).child(match_id).set({
                "worker_player": worker,
                "firm_player": firm,
                "worker_type": worker_type,
                "worker_action": None,
                "firm_action": None
            })

            players_ref.child(worker).update({
                "matched": True,
                "role": "Worker",
                "match_id": match_id
            })

            players_ref.child(firm).update({
                "matched": True,
                "role": "Firm",
                "match_id": match_id
            })

        st.success("Players matched!")
        st.rerun()


# --- PLAYER VIEW ---

st.header("🎮 Your Game")

if player_name in players:
    player_data = players[player_name]

    if player_data.get("matched"):
        role = player_data.get("role")
        match_id = player_data.get("match_id")

        match_data = db.reference(MATCHES_REF).child(match_id).get()

        st.subheader(f"Role: {role}")

        if role == "Worker":
            worker_type = match_data.get("worker_type")

            st.write(f"Your type: **{worker_type}**")

            if match_data.get("worker_action") is None:
                action = st.radio("Choose your action:", ["Effort", "No Effort"])

                if st.button("Submit Worker Action"):
                    db.reference(MATCHES_REF).child(match_id).update({
                        "worker_action": action
                    })
                    st.success("Action submitted!")
                    st.rerun()
            else:
                st.info(f"You chose: {match_data.get('worker_action')}")

        elif role == "Firm":
            if match_data.get("worker_action") is None:
                st.info("Waiting for worker's decision...")
            else:
                st.write(f"Worker chose: **{match_data.get('worker_action')}**")

                if match_data.get("firm_action") is None:
                    action = st.radio("Choose your response:", ["Manager", "Clerk"])

                    if st.button("Submit Firm Action"):
                        db.reference(MATCHES_REF).child(match_id).update({
                            "firm_action": action
                        })
                        st.success("Action submitted!")
                        st.rerun()
                else:
                    st.info(f"You chose: {match_data.get('firm_action')}")

# --- RESULTS & PAYOFFS ---

st.header("📊 Results")

all_matches = db.reference(MATCHES_REF).get() or {}

completed_matches = []
worker_actions = []
firm_actions = []
worker_types = []

for match_id, match_data in all_matches.items():
    if not isinstance(match_data, dict):
        continue

    if all(k in match_data and match_data[k] is not None for k in ["worker_action", "firm_action", "worker_type"]):
        worker_type = match_data["worker_type"]
        worker_action = match_data["worker_action"]
        firm_action = match_data["firm_action"]

        worker_payoff, firm_payoff = compute_payoffs(worker_type, worker_action, firm_action)

        completed_matches.append({
            "Match": match_id,
            "Worker": match_data.get("worker_player"),
            "Firm": match_data.get("firm_player"),
            "Type": worker_type,
            "Worker Action": worker_action,
            "Firm Action": firm_action,
            "Worker Payoff": worker_payoff,
            "Firm Payoff": firm_payoff
        })

        worker_actions.append(worker_action)
        firm_actions.append(firm_action)
        worker_types.append(worker_type)


if completed_matches:
    df = pd.DataFrame(completed_matches)
    st.dataframe(df)

    st.subheader("📈 Strategy Distributions")

    plot_enhanced_percentage_bar(worker_actions, ["Effort", "No Effort"], "Worker Actions", "Worker")
    plot_enhanced_percentage_bar(firm_actions, ["Manager", "Clerk"], "Firm Actions", "Firm")
    plot_enhanced_percentage_bar(worker_types, ["High", "Low"], "Worker Types", "Worker")

    # Average payoffs
    avg_worker_payoff = df["Worker Payoff"].mean()
    avg_firm_payoff = df["Firm Payoff"].mean()

    st.subheader("💰 Average Payoffs")
    st.write(f"Worker: **{avg_worker_payoff:.2f}**")
    st.write(f"Firm: **{avg_firm_payoff:.2f}**")

else:
    st.info("No completed matches yet.")


# --- DOWNLOAD PDF REPORT ---

st.header("📄 Export Results")

if st.button("Generate PDF Report"):
    with st.spinner("Generating report..."):
        pdf_bytes = create_pdf_report()

        st.download_button(
            label="📥 Download PDF",
            data=pdf_bytes,
            file_name="job_market_results.pdf",
            mime="application/pdf"
        )


# --- RESET GAME (OPTIONAL ADMIN TOOL) ---

st.header("⚙ Admin Controls")

if st.button("Reset Game"):
    db.reference(PLAYERS_REF).delete()
    db.reference(MATCHES_REF).delete()
    st.success("Game reset complete.")
    st.rerun()
