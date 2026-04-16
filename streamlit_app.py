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

# Firebase credentials and config
try:
    database_url = st.secrets["database_url"]

    # Build service account dict directly from TOML secrets
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
        firebase_admin.initialize_app(cred, {
            "databaseURL": database_url
        })

except KeyError:
    st.error("🔥 Firebase secrets not configured.")
    st.stop()

# Enhanced chart function
def plot_enhanced_percentage_bar(choices, labels, title, player_type):
    if len(choices) > 0:
        counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0) * 100
        
        # Create figure with enhanced styling
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('#f0f0f0')
        ax.set_facecolor('#e0e0e0')
        
        # Color scheme based on player type
        colors_scheme = ['#e74c3c', '#3498db'] if player_type == "Worker" else ['#3498db', '#e74c3c']
        
        # Create bar plot with enhanced styling
        bars = counts.plot(kind='bar', ax=ax, color=colors_scheme, linewidth=2, width=0.7)
        
        # Enhanced styling
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel("Percentage (%)", fontsize=14)
        ax.set_xlabel("Choice", fontsize=14)
        ax.tick_params(rotation=0, labelsize=12)
        ax.set_ylim(0, max(100, counts.max() * 1.1))
        
        # Add grid for better readability
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        # Add value labels on bars
        for i, bar in enumerate(ax.patches):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{height:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        # Add sample size info
        ax.text(0.02, 0.98, f"Sample size: {len(choices)} participants", 
               transform=ax.transAxes, fontsize=10, verticalalignment='top', alpha=0.7,
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # Add current date
        today = datetime.today().strftime('%B %d, %Y')
        ax.text(0.98, 0.98, f"Generated: {today}", transform=ax.transAxes, 
               fontsize=10, verticalalignment='top', horizontalalignment='right', alpha=0.7)
        
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.warning(f"⚠ No data available for {title}")

# PDF generation function for admin
def create_pdf_report():
    """Create a comprehensive PDF report using matplotlib figures"""
    from matplotlib.backends.backend_pdf import PdfPages
    import tempfile
    
    # Create temporary PDF file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    
    with PdfPages(temp_file.name) as pdf:
        # Get all completed matches
        all_matches = db.reference("job_matches").get() or {}
        results_data = []
        
        for match_id, match_data in all_matches.items():
            if "worker_choice" in match_data:
                ability = match_data["worker_ability"]
                worker_choice = match_data["worker_choice"]
                firm_choice = match_data.get("firm_choice", None)  # May be None if No Effort
                
                # Calculate payoffs
                if worker_choice == "No Effort":
                    worker_payoff, firm_payoff = 4, 4
                else:  # Effort
                    if ability == "High":
                        if firm_choice == "Manager":
                            worker_payoff, firm_payoff = 6, 10
                        else:  # Clerk
                            worker_payoff, firm_payoff = 0, 4
                    else:  # Low
                        if firm_choice == "Manager":
                            worker_payoff, firm_payoff = 3, 0
                        else:  # Clerk
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
            # Create summary page
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Job Market Signaling Game - Complete Results', fontsize=20, fontweight='bold')
            
            # Collect data for charts
            worker_choices = [r["Worker_Choice"] for r in results_data]
            firm_choices = [r["Firm_Choice"] for r in results_data if r["Firm_Choice"] != "N/A"]
            abilities = [r["Worker_Ability"] for r in results_data]
            
            # Chart 1: Worker Choices
            choice_counts = pd.Series(worker_choices).value_counts(normalize=True) * 100
            ax1.bar(choice_counts.index, choice_counts.values, color=['#e74c3c', '#3498db'], alpha=0.8)
            ax1.set_title('Worker Effort Choices', fontweight='bold')
            ax1.set_ylabel('Percentage (%)')
            for i, v in enumerate(choice_counts.values):
                ax1.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
            ax1.grid(True, alpha=0.3)
            
            # Chart 2: Firm Responses (when effort)
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
            
            # Chart 3: Ability Distribution
            ability_counts = pd.Series(abilities).value_counts(normalize=True) * 100
            ax3.bar(ability_counts.index, ability_counts.values, color=['#e74c3c', '#2ecc71'], alpha=0.8)
            ax3.set_title('Worker Ability Distribution', fontweight='bold')
            ax3.set_ylabel('Percentage (%)')
            for i, v in enumerate(ability_counts.values):
                ax3.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
            ax3.grid(True, alpha=0.3)
            
            # Chart 4: Strategy Analysis (pooling vs separating)
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
            
            # Create detailed results table page
            fig, ax = plt.subplots(figsize=(16, 10))
            ax.axis('tight')
            ax.axis('off')
            
            # Create table data
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
            
            # Style the table
            for i in range(len(table_data[0])):
                table[(0, i)].set_facecolor('#4472C4')
                table[(0, i)].set_text_props(weight='bold', color='white')
            
            ax.set_title('Detailed Game Results', fontsize=16, fontweight='bold', pad=20)
            pdf.savefig(fig, bbox_inches='tight', dpi=300)
            plt.close(fig)
    
    # Read the PDF file content
    with open(temp_file.name, 'rb') as f:
        pdf_content = f.read()
    
    # Clean up temp file
    import os
    os.unlink(temp_file.name)
    
    return pdf_content

# Admin section
admin_password = st.text_input("Admin Password:", type="password")

if admin_password == "admin123":
    st.header("🎓 Admin Control Panel")
    
    # Get real-time data with safe handling
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
    
    # Calculate statistics
    total_registered = len(all_players)
    worker_players = []
    firm_players = []
    
    for player in all_players.values():
        if player and isinstance(player, dict):
            role = player.get("role")
            if role == "Worker":
                worker_players.append(player)
            elif role == "Firm":
                firm_players.append(player)
    
    completed_matches = 0
    for match_data in all_matches.values():
        if match_data and isinstance(match_data, dict) and "worker_choice" in match_data:
            # Check if firm decision is made when effort was chosen
            if match_data["worker_choice"] == "No Effort":
                completed_matches += 1
            elif "firm_choice" in match_data:
                completed_matches += 1
    
    # Live Statistics Dashboard
    st.subheader("📊 Live Game Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Expected Players", expected_players)
    with col2:
        st.metric("Registered Players", total_registered)
    with col3:
        st.metric("Workers", len(worker_players))
    with col4:
        st.metric("Firms", len(firm_players))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Matches", len(all_matches))
    with col2:
        st.metric("Completed Matches", completed_matches)
    with col3:
        high_count = len([p for p in worker_players if isinstance(p, dict) and p.get("ability") == "High"])
        st.metric("High Ability Workers", high_count)
    
    # Player activity monitor
    st.subheader("👥 Player Activity Monitor")
    
    if all_players:
        player_status = []
        for name, player_data in all_players.items():
            role = player_data.get("role", "Unknown")
            status = "🔴 Registered"
            activity = "Waiting for match"
            
            # Find player's match
            player_match = None
            for match_id, match_data in all_matches.items():
                if name in [match_data.get("worker_player"), match_data.get("firm_player")]:
                    player_match = match_data
                    break
            
            if player_match:
                if role == "Worker":
                    if "worker_choice" in player_match:
                        status = "🟢 Completed"
                        activity = f"Chose: {player_match['worker_choice']}"
                    else:
                        status = "🟡 In Match"
                        activity = "Making effort decision..."
                elif role == "Firm":
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
            
            extra_info = ""
            if role == "Worker":
                ability = player_data.get("ability", "Unknown")
                extra_info = f"({ability})"
            
            player_status.append({
                "Player Name": name,
                "Role": role,
                "Status": status,
                "Activity": activity,
                "Extra Info": extra_info
            })
        
        status_df = pd.DataFrame(player_status)
        st.dataframe(status_df, use_container_width=True)
    
    # Live analytics
    st.subheader("📈 Live Game Analytics")
    
    if completed_matches > 0:
        # Collect data for charts
        worker_choices = []
        firm_choices = []
        abilities = []
        
        for match_data in all_matches.values():
            if match_data and isinstance(match_data, dict) and "worker_choice" in match_data:
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
            
            # Strategy analysis
            strategies = []
            for match_data in all_matches.values():
                if match_data and isinstance(match_data, dict) and "worker_choice" in match_data:
                    ability = match_data["worker_ability"]
                    choice = match_data["worker_choice"]
                    if ability == "Low" and choice == "No Effort":
                        strategies.append("Separating")
                    elif ability == "High" and choice == "Effort":
                        strategies.append("Separating")
                    else:
                        strategies.append("Pooling")
            
            if strategies:
                plot_enhanced_percentage_bar(strategies, ["Pooling", "Separating"], "Worker Strategy Analysis", "Worker")
    else:
        st.info("No completed matches yet. Charts will appear when players start completing games.")
    
    # Game Configuration
    st.subheader("⚙️ Game Configuration")
    current_expected = db.reference("job_expected_players").get() or 0
    st.write(f"Current expected players: {current_expected}")
    
    new_expected_players = st.number_input(
        "Set expected number of players:", 
        min_value=0, 
        max_value=100, 
        value=current_expected,
        step=2,
        help="Must be an even number (players are paired)"
    )
    
    if st.button("⚙ Update Expected Players"):
        if new_expected_players % 2 == 0:  # Must be even for pairing
            db.reference("job_expected_players").set(new_expected_players)
            st.success(f"✅ Expected players set to {new_expected_players}")
            st.rerun()
        else:
            st.error("⚠ Number of players must be even (for pairing)")
    
    # Data management
    st.subheader("🗂️ Data Management")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 Export Results (PDF)"):
            if completed_matches > 0:
                with st.spinner("Generating PDF report..."):
                    try:
                        pdf_content = create_pdf_report()
                        st.download_button(
                            label="📥 Download PDF Report",
                            data=pdf_content,
                            file_name="job_market_game_results.pdf",
                            mime="application/pdf"
                        )
                        st.success("✅ PDF report generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating PDF: {str(e)}")
                        # Fallback to CSV if PDF fails
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
                        
                        df = pd.DataFrame(results_data)
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download CSV (Fallback)",
                            data=csv,
                            file_name="job_market_game_results.csv",
                            mime="text/csv"
                        )
            else:
                st.warning("No completed matches to export.")
    
    with col2:
        if st.button("🗑️ Clear All Game Data"):
            db.reference("job_players").delete()
            db.reference("job_matches").delete()
            db.reference("job_expected_players").set(0)
            st.success("🧹 ALL game data cleared!")
            st.rerun()
    
    # Auto-refresh control and show complete results
    if expected_players > 0 and completed_matches < (expected_players // 2):
        # Auto-refresh while game is active
        time.sleep(3)
        st.rerun()
    elif completed_matches >= (expected_players // 2) and expected_players > 0:
        st.success("🎉 All matches completed! Game finished.")
        
        # Show the same Summary Analysis that participants see
        st.header("📊 Admin View: Summary Analysis - Class Results vs Game Theory")
        
        # Collect all results (same as participant view)
        worker_choices = []
        firm_choices = []
        abilities = []
        high_effort = []
        low_effort = []
        manager_responses = []
        
        for match_data in all_matches.values():
            if match_data and isinstance(match_data, dict) and "worker_choice" in match_data:
                ability = match_data["worker_ability"]
                choice = match_data["worker_choice"]
                
                worker_choices.append(choice)
                abilities.append(ability)
                
                # Separate by ability
                if ability == "High":
                    high_effort.append(choice)
                else:
                    low_effort.append(choice)
                
                if choice == "Effort" and "firm_choice" in match_data:
                    firm_choice = match_data["firm_choice"]
                    firm_choices.append(firm_choice)
                    # Track responses when effort is made
                    manager_responses.append(firm_choice)
        
        # Show key strategic analysis (same as participants see)
        st.subheader("🎯 Key Strategic Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            # % of high vs low ability choosing Effort
            if high_effort and low_effort:
                high_effort_pct = len([c for c in high_effort if c == "Effort"]) / len(high_effort) * 100
                low_effort_pct = len([c for c in low_effort if c == "Effort"]) / len(low_effort) * 100
                
                fig, ax = plt.subplots(figsize=(8, 5))
                categories = ['High Ability', 'Low Ability']
                percentages = [high_effort_pct, low_effort_pct]
                colors = ['#e74c3c', '#2ecc71']
                
                bars = ax.bar(categories, percentages, color=colors, alpha=0.8)
                ax.set_title("% Choosing Effort by Worker Ability", fontsize=14, fontweight='bold')
                ax.set_ylabel("Percentage (%)")
                ax.set_ylim(0, 110)
                
                # Add value labels
                for bar, pct in zip(bars, percentages):
                    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                           f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
                
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.info("Need both high and low ability workers to show this analysis")
        
        with col2:
            # % of firms offering Manager when effort is made
            if manager_responses:
                manager_pct = len([r for r in manager_responses if r == "Manager"]) / len(manager_responses) * 100
                
                fig, ax = plt.subplots(figsize=(8, 5))
                categories = ['Manager', 'Clerk']
                manager_count = len([r for r in manager_responses if r == "Manager"])
                clerk_count = len([r for r in manager_responses if r == "Clerk"])
                
                values = [manager_count, clerk_count]
                percentages_vals = [v/len(manager_responses)*100 for v in values]
                colors = ['#3498db', '#e74c3c']
                
                bars = ax.bar(categories, percentages_vals, color=colors, alpha=0.8)
                ax.set_title("Firm Job Offers (after Effort)", fontsize=14, fontweight='bold')
                ax.set_ylabel("Percentage (%)")
                ax.set_ylim(0, 110)
                
                # Add value labels
                for bar, pct in zip(bars, percentages_vals):
                    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                           f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
                
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.info("No effort choices made yet")
        
        # Game Theory Analysis (same as participants see)
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
        
        # Bayesian Analysis
        st.subheader("🔍 Bayesian Analysis")
        if manager_responses:
            manager_pct = len([r for r in manager_responses if r == "Manager"]) / len(manager_responses) * 100
            st.info(f"""
            **Key Insight**: When you see a worker choosing **Effort**, what's the probability they are High ability?
            
            **Your Class Results**: 
            - {len(manager_responses)} effort choices were made
            - Firms offered Manager {len([r for r in manager_responses if r == "Manager"])} times ({manager_pct:.1f}%)
            
            **Theoretical Prediction**: 
            - P(High | Effort) ≈ 100% in separating equilibrium
            - Effort is a credible signal of high ability when low types find it too costly to mimic.
            """)
        
        st.success("🎉 **Job Market Signaling Game Complete!** Students experienced signaling, screening, and Bayesian updating in action!")
        
        if st.button("🔄 Manual Refresh"):
            st.rerun()
    elif st.button("🔄 Refresh Dashboard"):
        st.rerun()
    
    st.divider()
    st.info("👨‍🏫 **Admin Dashboard**: Monitor game progress and analyze results in real-time.")
    
    # Stop here - admin doesn't participate
    st.stop()

# Check if game is configured
if (db.reference("job_expected_players").get() or 0) <= 0:
    st.info("⚠️ Game not configured yet. Admin needs to set expected number of players.")
    st.stop()

# Game explanation
st.header("📖 Simple Explanation of the Game")

st.markdown("""
This is a **job market signaling game** between two players:

👩‍💼 **Worker** (the sender of the signal/effort)  
🏢 **Firm** (the receiver, who decides which job to offer)

### 🎯 What's happening?

1. **Nature decides** the worker's ability: **High (33.3%)** or **Low (66.7%)**
2. **Worker chooses** to put in **Effort** (e.g., education, certification) or **No Effort**
3. **If worker chooses No Effort** → Game ends with payoffs (4,4)
4. **If worker chooses Effort** → Firm decides:
   - **Manager position** (high responsibility)
   - **Clerk position** (low responsibility)

---

### 💰 Payoff Matrix (Worker's payoff, Firm's payoff):

**If Worker is High Ability (33.3%):**
- Effort → Manager: (6, 10)
- Effort → Clerk: (0, 4)
- No Effort: (4, 4)

**If Worker is Low Ability (66.7%):**
- Effort → Manager: (3, 0)
- Effort → Clerk: (-3, 4)
- No Effort: (4, 4)

### 🎮 Game Steps:

**Step 1**: Player Registration - Enter your name  
**Step 2**: Random Nature Draw - System assigns high/low ability (hidden from Firm)  
**Step 3**: Worker's Move - Choose Effort or No Effort  
**Step 4**: Firm's Response (if Effort) - Choose Manager or Clerk  
**Step 5**: Show Results - Reveal abilities, choices, and payoffs  
**Step 6**: Summary Analysis - Class results vs game theory predictions

---
""")

# Player registration
name = st.text_input("Enter your name to join the game:")

if name:
    st.success(f"👋 Welcome, {name}!")
    
    player_ref = db.reference(f"job_players/{name}")
    player_data = player_ref.get()
    
    if not player_data:
        # Register new player
        player_ref.set({
            "joined": True,
            "timestamp": time.time()
        })
        st.write("✅ You are registered!")
    
    # Check if all expected players registered
    expected_players = db.reference("job_expected_players").get() or 0
    all_players = db.reference("job_players").get() or {}
    registered_count = len(all_players)
    
    if registered_count < expected_players:
        st.info(f"⏳ Waiting for more players... ({registered_count}/{expected_players} registered)")
        st.info("🔄 Page will automatically update when all players join.")
        time.sleep(3)
        st.rerun()
    
    # All players registered - start matching process
    st.success(f"🎮 All {expected_players} players registered! Starting the game...")
    
    # Check if player already has role assigned
    existing_player = player_ref.get()
    if not existing_player or "role" not in existing_player:
        # Auto-assign roles fairly with safe handling
        try:
            current_players_raw = db.reference("job_players").get()
            current_players = current_players_raw if isinstance(current_players_raw, dict) else {}
        except:
            current_players = {}
        
        worker_count = 0
        firm_count = 0
        
        for player in current_players.values():
            if player and isinstance(player, dict):
                role = player.get("role")
                if role == "Worker":
                    worker_count += 1
                elif role == "Firm":
                    firm_count += 1
        
        # Assign role to balance teams
        if worker_count < (expected_players // 2):
            role = "Worker"
            # Step 2: Random Nature Draw - Assign ability (1/3 High, 2/3 Low)
            is_high = random.random() < 1/3
            ability = "High" if is_high else "Low"
            
            player_ref.update({
                "role": role,
                "ability": ability
            })
        else:
            role = "Firm"
            player_ref.update({"role": role})
    else:
        role = existing_player["role"]
    
    # Display player role
    player_info = player_ref.get()
    if not player_info:
        st.error("Failed to retrieve player information. Please refresh the page.")
        st.stop()
    role = player_info.get("role")
    
    if role == "Worker":
        ability = player_info.get("ability")
        st.success(f"👩‍💼 **You are the Worker (sender)**")
        if ability:
            st.info(f"🎴 **Step 2 - Nature's Decision**: Your ability is **{ability}** (probability: {1/3:.1%} High, {2/3:.1%} Low)")
            st.write(f"**This information is private** - the Firm does not know your true ability!")
        else:
            st.warning("Setting up your game info...")
            time.sleep(1)
            st.rerun()
    elif role == "Firm":
        st.success(f"🏢 **You are the Firm (receiver)**")
        st.info("🎴 You don't know the worker's true ability - you must infer it from their effort choice!")
    else:
        st.warning("Setting up your role...")
        time.sleep(1)
        st.rerun()
    
    # Matching system
    matches_ref = db.reference("job_matches")
    all_matches = matches_ref.get() or {}
    
    # Check if player already matched
    player_match_id = None
    for match_id, match_data in all_matches.items():
        if name in [match_data.get("worker_player"), match_data.get("firm_player")]:
            player_match_id = match_id
            break
    
    if not player_match_id:
        # Find a match with safe handling
        try:
            all_job_players_raw = db.reference("job_players").get()
            all_job_players = all_job_players_raw if isinstance(all_job_players_raw, dict) else {}
        except:
            all_job_players = {}
        
        if role == "Worker":
            # Find an unmatched Firm player
            unmatched_firm_players = []
            for player_name, player_data in all_job_players.items():
                if player_data and isinstance(player_data, dict) and player_data.get("role") == "Firm" and player_name != name:
                    # Check if this Firm player is already matched
                    already_matched = False
                    for match_data in all_matches.values():
                        if player_name == match_data.get("firm_player"):
                            already_matched = True
                            break
                    if not already_matched:
                        unmatched_firm_players.append(player_name)
            
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
        
        else:  # Firm player
            # Find an unmatched Worker player
            unmatched_worker_players = []
            for player_name, player_data in all_job_players.items():
                if player_data and isinstance(player_data, dict) and player_data.get("role") == "Worker" and player_name != name:
                    # Check if this Worker player is already matched
                    already_matched = False
                    for match_data in all_matches.values():
                        if player_name == match_data.get("worker_player"):
                            already_matched = True
                            break
                    if not already_matched:
                        unmatched_worker_players.append(player_name)
            
            if unmatched_worker_players:
                worker_partner = unmatched_worker_players[0]
                worker_player_data = all_job_players[worker_partner]
                match_id = f"{worker_partner}_vs_{name}"
                matches_ref.child(match_id).set({
                    "worker_player": worker_partner,
                    "firm_player": name,
                    "worker_ability": worker_player_data.get("ability"),
                    "timestamp": time.time()
                })
                player_match_id = match_id
                st.success(f"🤝 You are matched with Worker: {worker_partner}!")
    
    if not player_match_id:
        st.info("⏳ Waiting for a match partner...")
        time.sleep(2)
        st.rerun()
    
    # Game play
    match_ref = matches_ref.child(player_match_id)
    match_data = match_ref.get()
    
    if role == "Worker":
        st.subheader("💪 Step 3: Worker's Move - Choose Effort Level")
        
        if "worker_choice" not in match_data:
            ability = match_data["worker_ability"]
            
            st.write(f"**Reminder**: Your ability is {ability}")
            st.info("💡 **Strategic Note**: Effort can signal high ability, but it's costly for low-ability workers.")
            
            worker_choice = st.radio(
                "Choose your action:", 
                ["Effort", "No Effort"],
                help="Effort: You invest in education/training. No Effort: You do nothing."
            )
            
            # Show payoff preview based on choice
            if worker_choice == "No Effort":
                st.info("📊 If you choose **No Effort**, the game ends immediately with payoffs (4 for you, 4 for the Firm).")
            else:
                st.info("📊 If you choose **Effort**, the Firm will then decide whether to offer you a Manager or Clerk position.")
                if ability == "High":
                    st.info("   - Manager → You get 6, Firm gets 10")
                    st.info("   - Clerk → You get 0, Firm gets 4")
                else:
                    st.info("   - Manager → You get 3, Firm gets 0")
                    st.info("   - Clerk → You get -3, Firm gets 4")
            
            if st.button("Submit Choice"):
                match_ref.update({
                    "worker_choice": worker_choice,
                    "worker_timestamp": time.time()
                })
                st.success(f"✅ You chose: {worker_choice}")
                st.rerun()
        else:
            st.success(f"✅ You already submitted: {match_data['worker_choice']}")
            if match_data['worker_choice'] == "No Effort":
                st.info("⏳ Game complete. Waiting for results...")
            else:
                st.info("⏳ Waiting for Firm's response...")
            
            # Auto-refresh to check for firm response or final results
            if match_data['worker_choice'] == "No Effort" or "firm_choice" in match_data:
                pass  # will show results
            else:
                time.sleep(2)
                st.rerun()
    
    elif role == "Firm":
        st.subheader("🏢 Step 4: Firm's Response - Choose Job Offer")
        
        if "worker_choice" not in match_data:
            st.info("⏳ Waiting for Worker to make an effort decision...")
            time.sleep(2)
            st.rerun()
        
        elif match_data["worker_choice"] == "No Effort":
            st.info("📢 The worker chose **No Effort**. According to the game rules, the game ends with payoffs (4,4). No further decision needed.")
            # Auto-mark as completed (no firm choice needed)
            if "firm_choice" not in match_data:
                # Record that firm has no decision (to mark completion)
                match_ref.update({
                    "firm_choice": "No Decision Needed",
                    "firm_timestamp": time.time()
                })
                st.rerun()
        
        elif "firm_choice" not in match_data:
            worker_choice = match_data["worker_choice"]
            worker_player = match_data["worker_player"]
            
            st.info(f"💪 **{worker_player} chose: {worker_choice}**")
            st.write("🤔 **Strategic Decision**: The worker invested effort. What does that signal about their ability?")
            st.info("💡 **Think**: High-ability workers are more likely to invest effort because it's less costly for them.")
            
            firm_choice = st.radio(
                "Choose job offer:", 
                ["Manager", "Clerk"],
                help="Manager = High responsibility, Clerk = Low responsibility"
            )
            
            if st.button("Submit Offer"):
                match_ref.update({
                    "firm_choice": firm_choice,
                    "firm_timestamp": time.time()
                })
                st.success(f"✅ You offered the {firm_choice} position!")
                st.rerun()
        else:
            st.success(f"✅ You offered: {match_data['firm_choice']}")
    
    # Show results when both moves are complete (or No Effort case)
    if "worker_choice" in match_data:
        worker_choice = match_data["worker_choice"]
        if worker_choice == "No Effort":
            # Game ends immediately
            show_results = True
        elif "firm_choice" in match_data:
            show_results = True
        else:
            show_results = False
        
        if show_results:
            st.header("🎯 Step 5: Results - The Truth is Revealed!")
            
            worker_player = match_data["worker_player"]
            firm_player = match_data["firm_player"]
            ability = match_data["worker_ability"]
            worker_choice = match_data["worker_choice"]
            firm_choice = match_data.get("firm_choice", None)
            
            # Show the revelation
            st.subheader("🔍 What Really Happened:")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"**Worker's Ability**\n{ability}")
            with col2:
                st.info(f"**Worker's Choice**\n{worker_choice}")
            with col3:
                if firm_choice:
                    st.info(f"**Firm's Offer**\n{firm_choice}")
                else:
                    st.info(f"**Firm's Offer**\nNo offer (No Effort)")
            
            # Calculate payoffs
            if worker_choice == "No Effort":
                worker_payoff, firm_payoff = 4, 4
            else:
                if ability == "High":
                    if firm_choice == "Manager":
                        worker_payoff, firm_payoff = 6, 10
                    else:  # Clerk
                        worker_payoff, firm_payoff = 0, 4
                else:  # Low
                    if firm_choice == "Manager":
                        worker_payoff, firm_payoff = 3, 0
                    else:  # Clerk
                        worker_payoff, firm_payoff = -3, 4
            
            # Show payoffs with explanation
            st.subheader("💰 Final Payoffs:")
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"**Worker ({worker_player})**\nPayoff: {worker_payoff}")
            with col2:
                st.success(f"**Firm ({firm_player})**\nPayoff: {firm_payoff}")
            
            # Outcome explanation
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
            
            # Add Summary Analysis for Firm participants immediately after their match
            if role == "Firm":
                st.header("📊 Step 6: Summary Analysis - Class Results vs Game Theory")
                
                # Get all completed matches for analysis
                all_matches = db.reference("job_matches").get() or {}
                completed_results = []
                
                for match_data in all_matches.values():
                    if "worker_choice" in match_data:
                        ability = match_data["worker_ability"]
                        choice = match_data["worker_choice"]
                        firm_choice = match_data.get("firm_choice", None)
                        completed_results.append({
                            "ability": ability,
                            "choice": choice,
                            "firm_choice": firm_choice
                        })
                
                if len(completed_results) >= 1:
                    st.subheader("🎯 Key Strategic Insights")
                    
                    # Separate data by ability
                    high_choices = [r["choice"] for r in completed_results if r["ability"] == "High"]
                    low_choices = [r["choice"] for r in completed_results if r["ability"] == "Low"]
                    effort_responses = [r["firm_choice"] for r in completed_results if r["choice"] == "Effort" and r["firm_choice"]]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if high_choices and low_choices:
                            high_effort_pct = len([c for c in high_choices if c == "Effort"]) / len(high_choices) * 100
                            low_effort_pct = len([c for c in low_choices if c == "Effort"]) / len(low_choices) * 100
                            
                            fig, ax = plt.subplots(figsize=(8, 5))
                            categories = ['High Ability', 'Low Ability']
                            percentages = [high_effort_pct, low_effort_pct]
                            colors = ['#e74c3c', '#2ecc71']
                            
                            bars = ax.bar(categories, percentages, color=colors, alpha=0.8)
                            ax.set_title("% Choosing Effort by Ability", fontsize=14, fontweight='bold')
                            ax.set_ylabel("Percentage (%)")
                            ax.set_ylim(0, 110)
                            
                            for bar, pct in zip(bars, percentages):
                                ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                                       f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
                            
                            ax.grid(True, alpha=0.3)
                            plt.tight_layout()
                            st.pyplot(fig)
                        else:
                            st.info("More data needed for ability comparison")
                    
                    with col2:
                        if effort_responses:
                            manager_pct = len([r for r in effort_responses if r == "Manager"]) / len(effort_responses) * 100
                            
                            fig, ax = plt.subplots(figsize=(8, 5))
                            categories = ['Manager', 'Clerk']
                            percentages_vals = [manager_pct, 100 - manager_pct]
                            colors = ['#3498db', '#e74c3c']
                            
                            bars = ax.bar(categories, percentages_vals, color=colors, alpha=0.8)
                            ax.set_title("Firm Offers (after Effort)", fontsize=14, fontweight='bold')
                            ax.set_ylabel("Percentage (%)")
                            ax.set_ylim(0, 110)
                            
                            for bar, pct in zip(bars, percentages_vals):
                                ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                                       f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
                            
                            ax.grid(True, alpha=0.3)
                            plt.tight_layout()
                            st.pyplot(fig)
                        else:
                            st.info("No effort choices yet")
                    
                    # Game Theory Analysis
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
                    
                    # Bayesian Insight
                    st.subheader("🔍 Bayesian Insight")
                    if effort_responses:
                        st.success(f"""
                        **Key Discovery**: When you see a worker choosing **Effort**, the probability they are High ability is very high!
                        
                        **Your Experience**: {len(effort_responses)} effort choices made, firms offered Manager {len([r for r in effort_responses if r == "Manager"])} times.
                        
                        **Why?** High-ability workers find effort worthwhile (they get the manager job), while low-ability workers avoid effort because it's too costly and unlikely to lead to manager.
                        """)
                    
                    st.info("🎓 **You've experienced signaling and screening in the job market!**")
            
            # Check if all matches completed for results display
            expected_players = db.reference("job_expected_players").get() or 0
            all_matches = db.reference("job_matches").get() or {}
            completed_matches = 0
            for match_data in all_matches.values():
                if "worker_choice" in match_data:
                    if match_data["worker_choice"] == "No Effort":
                        completed_matches += 1
                    elif "firm_choice" in match_data:
                        completed_matches += 1
            
            expected_matches = expected_players // 2
            
            if completed_matches >= expected_matches:
                st.header("📊 Step 6: Summary Analysis - Class Results vs Game Theory")
                
                # Collect all results
                worker_choices = []
                firm_choices = []
                abilities = []
                high_effort = []
                low_effort = []
                effort_responses = []
                
                for match_data in all_matches.values():
                    if "worker_choice" in match_data:
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
                            effort_responses.append(firm_choice)
                
                # Show key visualization as requested
                st.subheader("🎯 Key Strategic Analysis")
                
                col1, col2 = st.columns(2)
                with col1:
                    if high_effort and low_effort:
                        high_effort_pct = len([c for c in high_effort if c == "Effort"]) / len(high_effort) * 100
                        low_effort_pct = len([c for c in low_effort if c == "Effort"]) / len(low_effort) * 100
                        
                        fig, ax = plt.subplots(figsize=(8, 5))
                        categories = ['High Ability', 'Low Ability']
                        percentages = [high_effort_pct, low_effort_pct]
                        colors = ['#e74c3c', '#2ecc71']
                        
                        bars = ax.bar(categories, percentages, color=colors, alpha=0.8)
                        ax.set_title("% Choosing Effort by Worker Ability", fontsize=14, fontweight='bold')
                        ax.set_ylabel("Percentage (%)")
                        ax.set_ylim(0, 110)
                        
                        for bar, pct in zip(bars, percentages):
                            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                                   f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
                        
                        ax.grid(True, alpha=0.3)
                        plt.tight_layout()
                        st.pyplot(fig)
                    else:
                        st.info("Need both high and low ability workers to show this analysis")
                
                with col2:
                    if effort_responses:
                        manager_pct = len([r for r in effort_responses if r == "Manager"]) / len(effort_responses) * 100
                        
                        fig, ax = plt.subplots(figsize=(8, 5))
                        categories = ['Manager', 'Clerk']
                        manager_count = len([r for r in effort_responses if r == "Manager"])
                        clerk_count = len([r for r in effort_responses if r == "Clerk"])
                        
                        values = [manager_count, clerk_count]
                        percentages_vals = [v/len(effort_responses)*100 for v in values]
                        colors = ['#3498db', '#e74c3c']
                        
                        bars = ax.bar(categories, percentages_vals, color=colors, alpha=0.8)
                        ax.set_title("Firm Job Offers (after Effort)", fontsize=14, fontweight='bold')
                        ax.set_ylabel("Percentage (%)")
                        ax.set_ylim(0, 110)
                        
                        for bar, pct in zip(bars, percentages_vals):
                            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                                   f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
                        
                        ax.grid(True, alpha=0.3)
                        plt.tight_layout()
                        st.pyplot(fig)
                    else:
                        st.info("No effort choices made yet")
                
                # Game Theory Analysis
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
                
                # Bayesian Analysis
                st.subheader("🔍 Bayesian Analysis")
                if effort_responses:
                    st.info(f"""
                    **Key Insight**: When you see a worker choosing **Effort**, what's the probability they are High ability?
                    
                    **Your Class Results**: 
                    - {len(effort_responses)} effort choices were made
                    - Firms offered Manager {len([r for r in effort_responses if r == "Manager"])} times ({manager_pct:.1f}%)
                    
                    **Theoretical Prediction**: 
                    - P(High | Effort) ≈ 100% in separating equilibrium
                    - Effort is a credible signal when low types find it too costly.
                    """)
                
                st.success("🎉 **Job Market Signaling Game Complete!** You've experienced signaling, screening, and Bayesian updating in action!")

# Show game status
st.sidebar.header("🎮 Game Status")
try:
    players_raw = db.reference("job_players").get()
    players = players_raw if isinstance(players_raw, dict) else {}
    expected = db.reference("job_expected_players").get() or 0
except:
    players = {}
    expected = 0

registered = len(players)

st.sidebar.write(f"**Players**: {registered}/{expected}")

if expected > 0:
    progress = min(registered / expected, 1.0)
    st.sidebar.progress(progress)
