import json

def load_match_data(file_path):
    """
    Load match data from a JSON file
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        dict: Match data as a dictionary
    """
    try:
        with open(file_path, 'r') as file:
            match_data = json.load(file)
        return match_data
    except Exception as e:
        print(f"Error loading match data: {e}")
        return None

def calculate_player_minutes(match_data):
    """
    Calculate minutes played by each player based on the specified rules
    
    Args:
        match_data (dict): Match data containing formations, substitutions, and expulsions
        
    Returns:
        dict: Dictionary mapping player names to minutes played
    """
    if not match_data:
        return {}
    
    # Total match duration is 80 minutes plus recovery time
    recovery_minutes = match_data.get('recupero', 0)
    total_minutes = 80 + recovery_minutes  
    player_minutes = {}
    
    # Get the list of starting players (first 11 in formation)
    starting_players = match_data.get('formazione', [])[0:11]
    bench_players = match_data.get('formazione', [])[11:]
    
    # Initialize minutes for all players in the squad
    for player in match_data.get('formazione', []):
        if player:  # Skip empty strings
            player_minutes[player] = 0
    
    # Set initial minutes for starting players (assume they play the full match unless subbed/expelled)
    for player in starting_players:
        if player:  # Skip empty strings
            player_minutes[player] = total_minutes
    
    # Create dictionaries to easily look up substitution times
    sub_in_times = {}
    sub_out_times = {}
    
    for sub in match_data.get('substitutions', []):
        sub_in_player = sub.get('sub_out')  # Invertito come richiesto
        sub_out_player = sub.get('sub_in')  # Invertito come richiesto
        time_sub = sub.get('time_sub')
        
        if sub_in_player:
            sub_in_times[sub_in_player] = time_sub
        if sub_out_player:
            sub_out_times[sub_out_player] = time_sub
    
    # Create dictionary to look up expulsion times
    expulsion_times = {}
    
    for expulsion in match_data.get('espulsioni', []):
        if isinstance(expulsion, dict) and 'esp_player' in expulsion and 'time_esp' in expulsion:
            expelled_player = expulsion.get('esp_player')
            time_esp = expulsion.get('time_esp')
            expulsion_times[expelled_player] = time_esp
    
    # Calculate minutes for each player based on substitutions and expulsions
    for player in player_minutes:
        is_starter = player in starting_players
        is_sub_in = player in sub_in_times
        is_sub_out = player in sub_out_times
        is_expelled = player in expulsion_times
        
        # Apply the rules based on player's status
        if is_starter:
            # Regola 3: Starting player subbed out
            if is_sub_out:
                player_minutes[player] = sub_out_times[player]
            
            # Regola 4: Starting player expelled
            if is_expelled:
                player_minutes[player] = expulsion_times[player]
            
            # Regola 5: Starting player expelled and subbed out
            if is_expelled and is_sub_out:
                player_minutes[player] = min(expulsion_times[player], sub_out_times[player])
                
            # Se il giocatore è titolare e non appare in nessuna sostituzione o espulsione, gioca tutti i minuti
            if not is_sub_out and not is_expelled:
                player_minutes[player] = total_minutes
        else:
            # Regola 1: Bench player subbed in
            if is_sub_in and not is_sub_out and not is_expelled:
                player_minutes[player] = total_minutes - sub_in_times[player]
                
            # Regola 2: Player subbed in and later subbed out
            if is_sub_in and is_sub_out:
                player_minutes[player] = sub_out_times[player] - sub_in_times[player]
                
            # Regola 6: Player subbed in, subbed out, and expelled
            if is_sub_in and is_sub_out and is_expelled:
                # They play from sub_in to min(sub_out, expulsion)
                end_time = min(sub_out_times[player], expulsion_times[player])
                player_minutes[player] = end_time - sub_in_times[player]
                
            # Player subbed in and expelled
            elif is_sub_in and is_expelled:
                player_minutes[player] = expulsion_times[player] - sub_in_times[player]
    
    return player_minutes

def get_player_status(match_data):
    """
    Get the status of each player (starter, sub, not used, not called)
    
    Args:
        match_data (dict): Match data
        
    Returns:
        dict: Dictionary mapping player names to their status
    """
    player_status = {}
    player_detailed_status = {}
    
    # Mark starters
    starters = match_data.get('formazione', [])[0:11]
    for player in starters:
        if player:
            player_status[player] = "Titolare"
            player_detailed_status[player] = ["Titolare"]
    
    # Mark bench players
    bench = match_data.get('formazione', [])[11:]
    for player in bench:
        if player:
            player_status[player] = "Panchina"
            player_detailed_status[player] = ["Panchina"]
    
    # Initialize all players as not subbed in/out
    for player in match_data.get('formazione', []):
        if player:
            player_detailed_status.setdefault(player, [])
    
    # Mark substituted players - with new inverted logic
    for sub in match_data.get('substitutions', []):
        sub_in_player = sub.get('sub_out')  # Invertito come richiesto
        sub_out_player = sub.get('sub_in')  # Invertito come richiesto
        
        if sub_in_player and sub_in_player in player_detailed_status:
            player_status[sub_in_player] = "Subentrato"
            player_detailed_status[sub_in_player].append("Subentrato")
        
        if sub_out_player and sub_out_player in player_detailed_status:
            player_detailed_status[sub_out_player].append("Sostituito")
    
    # Mark players with yellow cards
    for player in match_data.get('ammonizioni', []):
        if player in player_status:
            player_status[player] += " (Ammonito)"
            player_detailed_status[player].append("Ammonito")
    
    # Mark expelled players
    for expulsion in match_data.get('espulsioni', []):
        if isinstance(expulsion, dict) and 'esp_player' in expulsion:
            expelled_player = expulsion.get('esp_player')
            if expelled_player in player_status:
                player_status[expelled_player] += " (Espulso)"
                player_detailed_status[expelled_player].append("Espulso")
        elif isinstance(expulsion, str):
            if expulsion in player_status:
                player_status[expulsion] += " (Espulso)"
                player_detailed_status[expulsion].append("Espulso")
    
    # Mark goal scorers
    for player in match_data.get('goal', []):
        if player in player_status:
            player_status[player] += " (Gol)"
            player_detailed_status[player].append("Gol")
    
    # Mark not called players
    for nc in match_data.get('non_convocati', []):
        player = nc.get('giocatore')
        reason = nc.get('motivo')
        player_status[player] = f"Non Convocato ({reason})"
        player_detailed_status[player] = [f"Non Convocato ({reason})"]
    
    # Check for players who didn't enter the match
    for player in bench:
        if player and player in player_detailed_status:
            if len(player_detailed_status[player]) == 1 and "Panchina" in player_detailed_status[player]:
                player_detailed_status[player].append("Non Entrato")
    
    # Format detailed status for display
    for player in player_detailed_status:
        player_status[player] = " | ".join(player_detailed_status[player])
    
    return player_status

def format_minutes(minutes):
    """Format minutes to handle special cases"""
    if minutes < 0:
        return "0"
    return str(minutes)

def get_match_summary(match_data):
    """
    Get a summary of the match
    
    Args:
        match_data (dict): Match data
        
    Returns:
        dict: Match summary information
    """
    summary = {
        'giornata': match_data.get('giornata'),
        'squadra': match_data.get('squadra'),
        'home_away': match_data.get('home_away'),
        'risultato': match_data.get('risultato'),
        'recupero': match_data.get('recupero')
    }
    return summary

def main(file_path):
    """
    Main function to calculate and display player minutes
    
    Args:
        file_path (str): Path to the JSON file
    
    Returns:
        tuple: (player_minutes, player_status, match_summary)
    """
    match_data = load_match_data(file_path)
    if not match_data:
        return {}, {}, {}
    
    player_minutes = calculate_player_minutes(match_data)
    player_status = get_player_status(match_data)
    match_summary = get_match_summary(match_data)
    
    # Sort players by minutes played (descending)
    sorted_players = sorted(
        [(player, minutes, player_status.get(player, "")) 
         for player, minutes in player_minutes.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    print("\nCalcolo dei minuti giocati:")
    print("===========================")
    for player, minutes, status in sorted_players:
        print(f"{player}: {format_minutes(minutes)} minuti - {status}")
    
    return player_minutes, player_status, match_summary

if __name__ == "__main__":
    # Test with the given JSON file
    json_file = "attached_assets/22_VIRTUS_PIONIERI.json"
    main(json_file)
