from nba_api.stats.endpoints import boxscoretraditionalv3

game_id = "0022300001"

boxscore = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
data = boxscore.get_dict()

# Print first 5 players
players = data["boxScoreTraditional"]["players"]
print(players[:5])
