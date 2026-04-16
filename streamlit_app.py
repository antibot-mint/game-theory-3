import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import time
import random
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="💼 Job Market Signaling Game")

st.title("💼 Job Market Signaling Game")

# -------------------- Firebase Setup --------------------
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

# -------------------- Helper Functions --------------------
def plot_enhanced_percentage_bar(choices, labels, title, player_type):
    if len(choices) > 0:
        counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0) * 100
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('#f0f0f0')
        ax.set_facecolor('#e0e0e0')
        colors_scheme = ['#e74c3c', '#3498db'] if player_type == "Worker" else ['#3498db', '#e74c3c']
        bars = counts.plot(kind='bar', ax=ax, color=colors_scheme, linewidth=2, width=0.7)
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel("Percentage (%)", fontsize=14)
        ax.set_xlabel("Choice", fontsize=14)
        ax.tick_params(rotation=0, labelsize=12)
        ax.set_ylim(0, max(100, counts.max() * 1.1))
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        for i, bar in enumerate(ax.patches):
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
    from matplotlib.backends.backend_pdf import PdfPages
    import tempfile
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    with PdfPages(temp_file.name) as pdf:
        all_matches = db.reference("job_matches").get() or {}
        results_data = []
        for match_id, match_data in all_matches.items():
            if "worker_choice" in match_data:
                ability = match_data["worker_ability"]
                worker_choice = match_data["worker_choice"]
                firm_choice = match_data.get("firm_choice", None)
                if worker_choice == "No Effort":
                    worker_payoff, firm_payoff = 4, 4
                else:
                    if ability == "High":
                        if firm_choice == "Manager":
                            worker_payoff, firm_payoff = 6, 10
                        else:
                            worker_payoff, firm_payoff = 0, 4
                    else:
                        if firm_choice == "Manager":
                            worker_payoff, firm_payoff = 3, 0
                        else:
                            worker_payoff, firm_payoff = -3, 4
                results_data.append({
                    "Match_ID": match_id,
                    "Worker_Player": match_data["worker_player"],
                    "Firm_Player": match_data["firm_player"],
                    "Worker_Ability": ability,
                    "Worker_Choice": worker_choice,
                    "Firm_Choice": firm_choice if firm_choice else "N/A",
                    "Worker_Payoff": worker_payoff,
                    "Firm_Payoff": firm_payoff
                })
        if results_data:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Job Market Signaling Game - Complete Results', fontsize=20, fontweight='bold')
            worker_choices = [r["Worker_Choice"] for r in results_data]
            firm_choices = [r["Firm_Choice"] for r in results_data if r["Firm_Choice"] != "N/A"]
            abilities = [r["Worker_Ability"] for r in results_data]
            choice_counts = pd.Series(worker_choices).value_counts(normalize=True) * 100
            ax1.bar(choice_counts.index, choice_counts.values, color=['#e74c3c', '#3498db'], alpha=0.8)
            ax1.set_title('Worker Effort Choices', fontweight='bold')
            ax1.set_ylabel('Percentage (%)')
            for i, v in enumerate(choice_counts.values):
                ax1.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
            ax1.grid(True, alpha=0.3)
            if firm_choices:
                firm_counts = pd.Series(firm_choices).value_counts(normalize=True) * 100
                ax2.bar(firm_counts.index, firm_counts.values, color=['#3498db', '#e74c3c'], alpha=0.8)
                ax2.set_title('Firm Job Offers (after Effort)', fontweight='bold')
                ax2.set_ylabel('Percentage (%)')
                for i, v in enumerate(firm_counts.values):
                    ax2.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
                ax2.grid(True, alpha=0.3)
            else:
                ax2.text(0.5, 0.5, 'No Effort choices made yet', ha='center', va='center')
            ability_counts = pd.Series(abilities).value_counts(normalize=True) * 100
            ax3.bar(ability_counts.index, ability_counts.values, color=['#e74c3c', '#2ecc71'], alpha=0.8)
            ax3.set_title('Worker Ability Distribution', fontweight='bold')
            ax3.set_ylabel('Percentage (%)')
            for i, v in enumerate(ability_counts.values):
                ax3.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
            ax3.grid(True, alpha=0.3)
            strategies = []
            for r in results_data:
                if r["Worker_Ability"] == "Low" and r["Worker_Choice"] == "No Effort":
                    strategies.append("Separating")
                elif r["Worker_Ability"] == "High" and r["Worker_Choice"] == "Effort":
                    strategies.append("Separating")
                else:
                    strategies.append("Pooling")
            if strategies:
                strategy_counts = pd.Series(strategies).value_counts(normalize=True) * 100
                ax4.bar(strategy_counts.index, strategy_counts.values, color=['#9b59b6', '#f39c12'], alpha=0.8)
                ax4.set_title('Worker Strategy Analysis', fontweight='bold')
                ax4.set_ylabel('Percentage (%)')
                for i, v in enumerate(strategy_counts.values):
                    ax4.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
                ax4.grid(True, alpha=0.3)
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight', dpi=300)
            plt.close(fig)
            # Detailed table
            fig, ax = plt.subplots(figsize=(16, 10))
            ax.axis('tight')
            ax.axis('off')
            table_data = [["Match ID", "Worker", "Firm", "Ability", "Worker Choice", "Firm Choice", "Worker Payoff", "Firm Payoff"]]
            for r in results_data:
                table_data.append([
                    r["Match_ID"], r["Worker_Player"], r["Firm_Player"],
                    r["Worker_Ability"], r["Worker_Choice"], r["Firm_Choice"],
                    str(r["Worker_Payoff"]), str(r["Firm_Payoff"])
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
    import os
    os.unlink(temp_file.name)
    return pdf_content

# -------------------- Admin Panel --------------------
admin_password = st.text_input("Admin Password:", type="password")
if admin_password == "admin123":
    st.header("🎓 Admin Control Panel")
    try:
        all_players_raw = db.reference("job_players").get()
        all_players = all_players_raw if isinstance(all_players_raw, dict) else {}
        all_matches_raw = db.reference("job_matches").get()
        all_matches = all_matches_raw if isinstance(all_matches_raw, dict) else {}
        expected_players = db.reference("job_expected_players").get() or 0
    except Exception as e:
        st.error("Error connecting to database. Please refresh the page.")
        all_players = {}
        all_matches = {}
        expected_players = 0

    total_registered = len(all_players)
    worker_players = [p for p in all_players.values() if p and p.get("role") == "Worker"]
    firm_players = [p for p in all_players.values() if p and p.get("role") == "Firm"]
    completed_matches = 0
    for match_data in all_matches.values():
        if match_data and "worker_choice" in match_data:
            if match_data["worker_choice"] == "No Effort" or "firm_choice" in match_data:
                completed_matches += 1

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Expected Players", expected_players)
    with col2: st.metric("Registered Players", total_registered)
    with col3: st.metric("Workers", len(worker_players))
    with col4: st.metric("Firms", len(firm_players))
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Total Matches", len(all_matches))
    with col2: st.metric("Completed Matches", completed_matches)
    with col3:
        high_count = len([p for p in worker_players if p.get("ability") == "High"])
        st.metric("High Ability Workers", high_count)

    st.subheader("👥 Player Activity Monitor")
    if all_players:
        player_status = []
        for name, player_data in all_players.items():
            role = player_data.get("role", "Unknown")
            status = "🔴 Registered"
            activity = "Waiting for match"
            paired_with = "Not yet matched"
            player_match = None
            for match_id, match_data in all_matches.items():
                if name in [match_data.get("worker_player"), match_data.get("firm_player")]:
                    player_match = match_data
                    break
            if player_match:
                if role == "Worker":
                    paired_with = player_match.get("firm_player", "Unknown")
                    if "worker_choice" in player_match:
                        status = "🟢 Completed"
                        activity = f"Chose: {player_match['worker_choice']}"
                    else:
                        status = "🟡 In Match"
                        activity = "Making effort decision..."
                elif role == "Firm":
                    paired_with = player_match.get("worker_player", "Unknown")
                    if "worker_choice" in player_match:
                        if player_match["worker_choice"] == "No Effort":
                            status = "🟢 Completed"
                            activity = "No effort → game ended"
                        elif "firm_choice" in player_match:
                            status = "🟢 Completed"
                            activity = f"Offered: {player_match['firm_choice']}"
                        else:
                            status = "🟡 In Match"
                            activity = "Waiting for worker effort..."
                    else:
                        status = "🟡 In Match"
                        activity = "Waiting for worker..."
            extra_info = f"({player_data.get('ability', 'Unknown')})" if role == "Worker" else ""
            player_status.append({
                "Player Name": name,
                "Role": role,
                "Paired With": paired_with,
                "Status": status,
                "Activity": activity,
                "Extra Info": extra_info
            })
        st.dataframe(pd.DataFrame(player_status), use_container_width=True)

    st.subheader("📈 Live Game Analytics")
    if completed_matches > 0:
        worker_choices = []
        firm_choices = []
        abilities = []
        for match_data in all_matches.values():
            if match_data and "worker_choice" in match_data:
                worker_choices.append(match_data["worker_choice"])
                abilities.append(match_data["worker_ability"])
                if match_data["worker_choice"] == "Effort" and "firm_choice" in match_data:
                    firm_choices.append(match_data["firm_choice"])
        col1, col2 = st.columns(2)
        with col1:
            plot_enhanced_percentage_bar(worker_choices, ["Effort", "No Effort"], "Worker Effort Choices", "Worker")
            plot_enhanced_percentage_bar(abilities, ["High", "Low"], "Worker Ability Distribution", "Worker")
        with col2:
            if firm_choices:
                plot_enhanced_percentage_bar(firm_choices, ["Manager", "Clerk"], "Firm Job Offers (after Effort)", "Firm")
            strategies = []
            for match_data in all_matches.values():
                if match_data and "worker_choice" in match_data:
                    ability = match_data["worker_ability"]
                    choice = match_data["worker_choice"]
                    if (ability == "Low" and choice == "No Effort") or (ability == "High" and choice == "Effort"):
                        strategies.append("Separating")
                    else:
                        strategies.append("Pooling")
            if strategies:
                plot_enhanced_percentage_bar(strategies, ["Pooling", "Separating"], "Worker Strategy Analysis", "Worker")
    else:
        st.info("No completed matches yet. Charts will appear when players start completing games.")

    st.subheader("⚙️ Game Configuration")
    current_expected = db.reference("job_expected_players").get() or 0
    st.write(f"Current expected players: {current_expected}")
    new_expected_players = st.number_input("Set expected number of players:", min_value=0, max_value=100, value=current_expected, step=2, help="Must be an even number (players are paired)")
    if st.button("⚙ Update Expected Players"):
        if new_expected_players % 2 == 0:
            db.reference("job_expected_players").set(new_expected_players)
            st.success(f"✅ Expected players set to {new_expected_players}")
            st.rerun()
        else:
            st.error("⚠ Number of players must be even (for pairing)")

    st.subheader("🎲 Role Management")
    if total_registered >= 2 and total_registered % 2 == 0:
        if st.button("👥 Assign Roles (randomly half Workers, half Firms)"):
            for pname in all_players.keys():
                db.reference(f"job_players/{pname}/role").delete()
                db.reference(f"job_players/{pname}/ability").delete()
            player_names = list(all_players.keys())
            random.shuffle(player_names)
            half = total_registered // 2
            worker_names = player_names[:half]
            firm_names = player_names[half:]
            for pname in worker_names:
                ability = "High" if random.random() < 1/3 else "Low"
                db.reference(f"job_players/{pname}").update({"role": "Worker", "ability": ability})
            for pname in firm_names:
                db.reference(f"job_players/{pname}").update({"role": "Firm"})
            db.reference("job_roles_assigned").set(True)
            st.success(f"✅ Roles assigned: {len(worker_names)} Workers, {len(firm_names)} Firms")
            st.rerun()
    else:
        st.info(f"Need at least 2 registered players and an even number to assign roles. Currently {total_registered} players.")

    if st.button("🔄 Reassign Roles (clear and reassign)"):
        for pname in all_players.keys():
            db.reference(f"job_players/{pname}/role").delete()
            db.reference(f"job_players/{pname}/ability").delete()
        db.reference("job_roles_assigned").delete()
        st.success("Roles cleared. Click 'Assign Roles' again when ready.")
        st.rerun()

    st.subheader("🗂️ Data Management")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📄 Export Results (PDF)"):
            if completed_matches > 0:
                with st.spinner("Generating PDF report..."):
                    try:
                        pdf_content = create_pdf_report()
                        st.download_button(label="📥 Download PDF Report", data=pdf_content, file_name="job_market_game_results.pdf", mime="application/pdf")
                        st.success("✅ PDF report generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating PDF: {str(e)}")
                        results_data = []
                        for match_id, match_data in all_matches.items():
                            if "worker_choice" in match_data:
                                ability = match_data["worker_ability"]
                                worker_choice = match_data["worker_choice"]
                                firm_choice = match_data.get("firm_choice", None)
                                if worker_choice == "No Effort":
                                    worker_payoff, firm_payoff = 4, 4
                                else:
                                    if ability == "High":
                                        if firm_choice == "Manager":
                                            worker_payoff, firm_payoff = 6, 10
                                        else:
                                            worker_payoff, firm_payoff = 0, 4
                                    else:
                                        if firm_choice == "Manager":
                                            worker_payoff, firm_payoff = 3, 0
                                        else:
                                            worker_payoff, firm_payoff = -3, 4
                                results_data.append({"Match_ID": match_id, "Worker_Player": match_data["worker_player"], "Firm_Player": match_data["firm_player"], "Worker_Ability": ability, "Worker_Choice": worker_choice, "Firm_Choice": firm_choice if firm_choice else "N/A", "Worker_Payoff": worker_payoff, "Firm_Payoff": firm_payoff})
                        df = pd.DataFrame(results_data)
                        st.download_button(label="📥 Download CSV (Fallback)", data=df.to_csv(index=False), file_name="job_market_game_results.csv", mime="text/csv")
            else:
                st.warning("No completed matches to export.")
    with col2:
        if st.button("🗑️ Clear All Game Data"):
            db.reference("job_players").delete()
            db.reference("job_matches").delete()
            db.reference("job_expected_players").set(0)
            db.reference("job_roles_assigned").delete()
            st.success("🧹 ALL game data cleared!")
            st.rerun()

    if expected_players > 0 and completed_matches < (expected_players // 2):
        time.sleep(3)
        st.rerun()
    elif completed_matches >= (expected_players // 2) and expected_players > 0:
        st.success("🎉 All matches completed! Game finished.")
        st.header("📊 Admin View: Summary Analysis - Class Results vs Game Theory")
        worker_choices = []
        firm_choices = []
        abilities = []
        high_effort = []
        low_effort = []
        manager_responses = []
        for match_data in all_matches.values():
            if match_data and "worker_choice" in match_data:
                ability = match_data["worker_ability"]
                choice = match_data["worker_choice"]
                worker_choices.append(choice)
                abilities.append(ability)
                if ability == "High":
                    high_effort.append(choice)
                else:
                    low_effort.append(choice)
                if choice == "Effort" and "firm_choice" in match_data:
                    firm_choice = match_data["firm_choice"]
                    firm_choices.append(firm_choice)
                    manager_responses.append(firm_choice)
        st.subheader("🎯 Key Strategic Analysis")
        col1, col2 = st.columns(2)
        with col1:
            if high_effort and low_effort:
                high_effort_pct = len([c for c in high_effort if c == "Effort"]) / len(high_effort) * 100
                low_effort_pct = len([c for c in low_effort if c == "Effort"]) / len(low_effort) * 100
                fig, ax = plt.subplots(figsize=(8, 5))
                categories = ['High Ability', 'Low Ability']
                percentages = [high_effort_pct, low_effort_pct]
                bars = ax.bar(categories, percentages, color=['#e74c3c', '#2ecc71'], alpha=0.8)
                ax.set_title("% Choosing Effort by Worker Ability", fontsize=14, fontweight='bold')
                ax.set_ylabel("Percentage (%)")
                ax.set_ylim(0, 110)
                for bar, pct in zip(bars, percentages):
                    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2, f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.info("Need both high and low ability workers to show this analysis")
        with col2:
            if manager_responses:
                manager_pct = len([r for r in manager_responses if r == "Manager"]) / len(manager_responses) * 100
                fig, ax = plt.subplots(figsize=(8, 5))
                manager_count = len([r for r in manager_responses if r == "Manager"])
                clerk_count = len([r for r in manager_responses if r == "Clerk"])
                values = [manager_count, clerk_count]
                percentages_vals = [v/len(manager_responses)*100 for v in values]
                bars = ax.bar(['Manager', 'Clerk'], percentages_vals, color=['#3498db', '#e74c3c'], alpha=0.8)
                ax.set_title("Firm Job Offers (after Effort)", fontsize=14, fontweight='bold')
                ax.set_ylabel("Percentage (%)")
                ax.set_ylim(0, 110)
                for bar, pct in zip(bars, percentages_vals):
                    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2, f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.info("No effort choices made yet")
        st.subheader("🧮 Game Theory Predictions vs Your Class")
        col1, col2, col3 = st.columns(3)
        with col1:
            if manager_responses:
                manager_pct = len([r for r in manager_responses if r == "Manager"]) / len(manager_responses) * 100
                st.metric("Firm Offers Manager (after Effort)", f"{manager_pct:.1f}%", "Theory: ~67%")
            else:
                st.metric("Firm Offers Manager", "N/A", "Theory: ~67%")
        with col2:
            if high_effort:
                high_effort_pct = len([c for c in high_effort if c == "Effort"]) / len(high_effort) * 100
                st.metric("High Ability Choose Effort", f"{high_effort_pct:.1f}%", "Theory: ~100%")
            else:
                st.metric("High Ability Choose Effort", "N/A", "Theory: ~100%")
        with col3:
            if low_effort:
                low_effort_pct = len([c for c in low_effort if c == "Effort"]) / len(low_effort) * 100
                st.metric("Low Ability Choose Effort", f"{low_effort_pct:.1f}%", "Theory: ~0%")
            else:
                st.metric("Low Ability Choose Effort", "N/A", "Theory: ~0%")
        st.success("🎉 **Job Market Signaling Game Complete!**")
        if st.button("🔄 Manual Refresh"):
            st.rerun()
    elif st.button("🔄 Refresh Dashboard"):
        st.rerun()
    st.divider()
    st.info("👨‍🏫 **Admin Dashboard**: Monitor game progress and analyze results in real-time.")
    st.stop()

# -------------------- Game Logic --------------------
if (db.reference("job_expected_players").get() or 0) <= 0:
    st.info("⚠️ Game not configured yet. Admin needs to set expected number of players.")
    st.stop()

st.header("📖 Simple Explanation of the Game")
st.markdown("""
This is a **job market signaling game** between two players:

👩‍💼 **Worker** (the sender of the signal/effort)  
🏢 **Firm** (the receiver, who decides which job to offer)

### 🎯 What's happening?
1. **Nature decides** the worker's ability: **High (33.3%)** or **Low (66.7%)**
2. **Worker chooses** to put in **Effort** (e.g., education, certification) or **No Effort**
3. **If worker chooses No Effort** → Game ends with payoffs (4,4)
4. **If worker chooses Effort** → Firm decides: **Manager** or **Clerk**

### 💰 Payoff Matrix (Worker, Firm):
**High Ability (33.3%):**  
- Effort → Manager: (6, 10)  
- Effort → Clerk: (0, 4)  
- No Effort: (4, 4)

**Low Ability (66.7%):**  
- Effort → Manager: (3, 0)  
- Effort → Clerk: (-3, 4)  
- No Effort: (4, 4)

### 🎮 Game Steps:
**Step 1**: Player Registration  
**Step 2**: Random Nature Draw (ability hidden from Firm)  
**Step 3**: Worker's Move (Effort or No Effort)  
**Step 4**: Firm's Response (Manager or Clerk, if Effort)  
**Step 5**: Show Results  
**Step 6**: Summary Analysis
""")

# Registration
name = st.text_input("Enter your name to join the game:")
if name:
    st.success(f"👋 Welcome, {name}!")
    player_ref = db.reference(f"job_players/{name}")
    player_data = player_ref.get()
    if not player_data:
        player_ref.set({"joined": True, "timestamp": time.time()})
        st.write("✅ You are registered!")

    # Check if roles have been assigned by the admin
    roles_assigned = db.reference("job_roles_assigned").get()
    if not roles_assigned:
        st.info("⏳ Waiting for admin to assign roles... (The game will start automatically once roles are assigned.)")
        time.sleep(3)
        st.rerun()

    # Roles are assigned – get the player's role
    player_info = player_ref.get()
    if not player_info or "role" not in player_info:
        st.error("Role not found. Please ask the admin to reassign roles.")
        st.stop()
    role = player_info["role"]

    if role == "Worker":
        ability = player_info.get("ability")
        st.success(f"👩‍💼 **You are the Worker (sender)**")
        if ability:
            st.info(f"🎴 **Step 2 - Nature's Decision**: Your ability is **{ability}** (probability: 33.3% High, 66.7% Low)")
            st.write(f"**This information is private** - the Firm does not know your true ability!")
        else:
            st.error("Ability missing. Please ask admin to reassign roles.")
            st.stop()
    elif role == "Firm":
        st.success(f"🏢 **You are the Firm (receiver)**")
    else:
        st.error("Invalid role. Please ask admin to reassign roles.")
        st.stop()

    # Matching
    expected_players = db.reference("job_expected_players").get() or 0
    matches_ref = db.reference("job_matches")
    all_matches = matches_ref.get() or {}
    player_match_id = None
    for match_id, match_data in all_matches.items():
        if name in [match_data.get("worker_player"), match_data.get("firm_player")]:
            player_match_id = match_id
            break

    if not player_match_id:
        all_job_players = db.reference("job_players").get() or {}
        if role == "Worker":
            unmatched_firm_players = []
            for pname, pdata in all_job_players.items():
                if pdata and pdata.get("role") == "Firm" and pname != name:
                    already_matched = any(pname == m.get("firm_player") for m in all_matches.values())
                    if not already_matched:
                        unmatched_firm_players.append(pname)
            if unmatched_firm_players:
                firm_partner = unmatched_firm_players[0]
                match_id = f"{name}_vs_{firm_partner}"
                matches_ref.child(match_id).set({
                    "worker_player": name,
                    "firm_player": firm_partner,
                    "worker_ability": ability,
                    "timestamp": time.time()
                })
                player_match_id = match_id
                st.success(f"🤝 You are matched with Firm: {firm_partner}!")
        else:  # Firm
            unmatched_worker_players = []
            for pname, pdata in all_job_players.items():
                if pdata and pdata.get("role") == "Worker" and pname != name:
                    already_matched = any(pname == m.get("worker_player") for m in all_matches.values())
                    if not already_matched:
                        unmatched_worker_players.append(pname)
            if unmatched_worker_players:
                worker_partner = unmatched_worker_players[0]
                worker_ability = all_job_players[worker_partner].get("ability")
                match_id = f"{worker_partner}_vs_{name}"
                matches_ref.child(match_id).set({
                    "worker_player": worker_partner,
                    "firm_player": name,
                    "worker_ability": worker_ability,
                    "timestamp": time.time()
                })
                player_match_id = match_id
                st.success(f"🤝 You are matched with Worker: {worker_partner}!")

    if not player_match_id:
        st.info("⏳ Waiting for a match partner...")
        time.sleep(2)
        st.rerun()

    # Gameplay
    match_ref = matches_ref.child(player_match_id)
    match_data = match_ref.get()

    if role == "Worker":
        st.subheader("💪 Step 3: Worker's Move - Choose Effort Level")
        if "worker_choice" not in match_data:
            ability = match_data["worker_ability"]
            st.write(f"**Reminder**: Your ability is {ability}")
            if ability == "High":
                st.info("""
**If you choose Effort**, the Firm will then decide whether to offer you a Manager or Clerk position.

- Manager → You get 6, Firm gets 10
- Clerk → You get 0, Firm gets 4

**If you choose No Effort**, the game ends immediately with payoffs (4 for you, 4 for the Firm).
""")
            else:
                st.info("""
**If you choose Effort**, the Firm will then decide whether to offer you a Manager or Clerk position.

- Manager → You get 3, Firm gets 0
- Clerk → You get -3, Firm gets 4

**If you choose No Effort**, the game ends immediately with payoffs (4 for you, 4 for the Firm).
""")
            worker_choice = st.radio("Choose your action:", ["Effort", "No Effort"])
            if st.button("Submit Choice"):
                match_ref.update({"worker_choice": worker_choice, "worker_timestamp": time.time()})
                st.success(f"✅ You chose: {worker_choice}")
                st.rerun()
        else:
            st.success(f"✅ You already submitted: {match_data['worker_choice']}")
            if match_data['worker_choice'] == "No Effort":
                st.info("⏳ Game complete. Waiting for results...")
            else:
                st.info("⏳ Waiting for Firm's response...")
            if match_data['worker_choice'] != "No Effort" and "firm_choice" not in match_data:
                time.sleep(2)
                st.rerun()

    elif role == "Firm":
        st.subheader("🏢 Step 4: Firm's Response - Choose Job Offer")
        # Force refresh of match_data each time
        match_data = match_ref.get()  # Re-fetch to get latest worker choice
        
        if "worker_choice" not in match_data:
            st.info("⏳ Waiting for Worker to make an effort decision...")
            # Auto-refresh every 2 seconds
            time.sleep(2)
            st.rerun()
        elif match_data["worker_choice"] == "No Effort":
            st.info("📢 The worker chose **No Effort**. The game ends with payoffs (4,4). No further decision needed.")
            if "firm_choice" not in match_data:
                match_ref.update({"firm_choice": "No Decision Needed", "firm_timestamp": time.time()})
                st.rerun()
        elif "firm_choice" not in match_data:
            worker_choice = match_data["worker_choice"]
            worker_player = match_data["worker_player"]
            st.info(f"💪 **{worker_player} chose: {worker_choice}**")
            firm_choice = st.radio("Choose job offer:", ["Manager", "Clerk"])
            if st.button("Submit Offer"):
                match_ref.update({"firm_choice": firm_choice, "firm_timestamp": time.time()})
                st.success(f"✅ You offered the {firm_choice} position!")
                st.rerun()
        else:
            st.success(f"✅ You offered: {match_data['firm_choice']}")

    # Show results when complete
    if "worker_choice" in match_data:
        worker_choice = match_data["worker_choice"]
        if worker_choice == "No Effort" or "firm_choice" in match_data:
            st.header("🎯 Step 5: Results - The Truth is Revealed!")
            worker_player = match_data["worker_player"]
            firm_player = match_data["firm_player"]
            ability = match_data["worker_ability"]
            worker_choice = match_data["worker_choice"]
            firm_choice = match_data.get("firm_choice", None)
            st.subheader("🔍 What Really Happened:")
            col1, col2, col3 = st.columns(3)
            with col1: st.info(f"**Worker's Ability**\n{ability}")
            with col2: st.info(f"**Worker's Choice**\n{worker_choice}")
            with col3: st.info(f"**Firm's Offer**\n{firm_choice if firm_choice else 'No offer (No Effort)'}")
            if worker_choice == "No Effort":
                worker_payoff, firm_payoff = 4, 4
            else:
                if ability == "High":
                    if firm_choice == "Manager":
                        worker_payoff, firm_payoff = 6, 10
                    else:
                        worker_payoff, firm_payoff = 0, 4
                else:
                    if firm_choice == "Manager":
                        worker_payoff, firm_payoff = 3, 0
                    else:
                        worker_payoff, firm_payoff = -3, 4
            st.subheader("💰 Final Payoffs:")
            col1, col2 = st.columns(2)
            with col1: st.success(f"**Worker ({worker_player})**\nPayoff: {worker_payoff}")
            with col2: st.success(f"**Firm ({firm_player})**\nPayoff: {firm_payoff}")
            if worker_choice == "No Effort":
                st.write("📉 **Outcome**: Worker chose no effort. Both parties receive baseline payoffs (4 each).")
                st.write("💡 **Insight**: Without effort, the firm cannot distinguish ability, so both get the same moderate payoff.")
            else:
                st.write("📈 **Outcome**: Worker invested effort, firm made a job offer based on that signal.")
                if ability == "High":
                    if firm_choice == "Manager":
                        st.write("✅ **Result**: High-ability worker got the manager position - efficient matching!")
                    else:
                        st.write("⚠️ **Result**: High-ability worker was underplaced as clerk - firm missed out!")
                else:
                    if firm_choice == "Manager":
                        st.write("⚠️ **Result**: Low-ability worker fooled the firm into giving them a manager job - bad for firm!")
                    else:
                        st.write("✅ **Result**: Low-ability worker correctly placed as clerk - good screening by firm.")
            st.balloons()
            st.success("✅ Your match is complete! Thank you for playing.")

            # Show summary for Firm participants - only Theory vs Your Class Results (no charts)
            if role == "Firm":
                st.header("📊 Step 6: Summary Analysis - Class Results vs Game Theory")
                all_matches = db.reference("job_matches").get() or {}
                completed_results = []
                for match_data in all_matches.values():
                    if "worker_choice" in match_data:
                        completed_results.append({
                            "ability": match_data["worker_ability"],
                            "choice": match_data["worker_choice"],
                            "firm_choice": match_data.get("firm_choice", None)
                        })
                if len(completed_results) >= 1:
                    high_choices = [r["choice"] for r in completed_results if r["ability"] == "High"]
                    low_choices = [r["choice"] for r in completed_results if r["ability"] == "Low"]
                    effort_responses = [r["firm_choice"] for r in completed_results if r["choice"] == "Effort" and r["firm_choice"]]
                    
                    st.subheader("🧮 Theory vs Your Class Results")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if effort_responses:
                            manager_pct = len([r for r in effort_responses if r == "Manager"]) / len(effort_responses) * 100
                            st.metric("Firm Offers Manager", f"{manager_pct:.1f}%", "Theory: ~67%")
                        else:
                            st.metric("Firm Offers Manager", "N/A", "Theory: ~67%")
                    with col2:
                        if high_choices:
                            high_effort_pct = len([c for c in high_choices if c == "Effort"]) / len(high_choices) * 100
                            st.metric("High Ability Choose Effort", f"{high_effort_pct:.1f}%", "Theory: ~100%")
                        else:
                            st.metric("High Ability Choose Effort", "N/A", "Theory: ~100%")
                    with col3:
                        if low_choices:
                            low_effort_pct = len([c for c in low_choices if c == "Effort"]) / len(low_choices) * 100
                            st.metric("Low Ability Choose Effort", f"{low_effort_pct:.1f}%", "Theory: ~0%")
                        else:
                            st.metric("Low Ability Choose Effort", "N/A", "Theory: ~0%")
                    st.info("🎓 **You've experienced signaling and screening in the job market!**")

            # Global summary after all matches complete - also only metrics
            expected_players = db.reference("job_expected_players").get() or 0
            all_matches = db.reference("job_matches").get() or {}
            completed_matches = 0
            for match_data in all_matches.values():
                if "worker_choice" in match_data:
                    if match_data["worker_choice"] == "No Effort" or "firm_choice" in match_data:
                        completed_matches += 1
            expected_matches = expected_players // 2
            if completed_matches >= expected_matches:
                st.header("📊 Step 6: Summary Analysis - Class Results vs Game Theory")
                high_effort = []
                low_effort = []
                effort_responses = []
                for match_data in all_matches.values():
                    if "worker_choice" in match_data:
                        ability = match_data["worker_ability"]
                        choice = match_data["worker_choice"]
                        if ability == "High":
                            high_effort.append(choice)
                        else:
                            low_effort.append(choice)
                        if choice == "Effort" and "firm_choice" in match_data:
                            effort_responses.append(match_data["firm_choice"])
                
                st.subheader("🧮 Game Theory Predictions vs Your Class")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if effort_responses:
                        manager_pct = len([r for r in effort_responses if r == "Manager"]) / len(effort_responses) * 100
                        st.metric("Firm Offers Manager (after Effort)", f"{manager_pct:.1f}%", "Theory: ~67%")
                    else:
                        st.metric("Firm Offers Manager", "N/A", "Theory: ~67%")
                with col2:
                    if high_effort:
                        high_effort_pct = len([c for c in high_effort if c == "Effort"]) / len(high_effort) * 100
                        st.metric("High Ability Choose Effort", f"{high_effort_pct:.1f}%", "Theory: ~100%")
                    else:
                        st.metric("High Ability Choose Effort", "N/A", "Theory: ~100%")
                with col3:
                    if low_effort:
                        low_effort_pct = len([c for c in low_effort if c == "Effort"]) / len(low_effort) * 100
                        st.metric("Low Ability Choose Effort", f"{low_effort_pct:.1f}%", "Theory: ~0%")
                    else:
                        st.metric("Low Ability Choose Effort", "N/A", "Theory: ~0%")
                st.success("🎉 **Job Market Signaling Game Complete!**")

# Sidebar status
st.sidebar.header("🎮 Game Status")
try:
    players = db.reference("job_players").get() or {}
    expected = db.reference("job_expected_players").get() or 0
except:
    players = {}
    expected = 0
registered = len(players)
st.sidebar.write(f"**Players**: {registered}/{expected}")
if expected > 0:
    st.sidebar.progress(min(registered / expected, 1.0))
