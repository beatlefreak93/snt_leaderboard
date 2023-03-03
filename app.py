from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from builtins import round
from sqlalchemy import text
from sqlalchemy.orm import aliased


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tennis.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.app_context().push()

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    win_rate = db.Column(db.Float, default=0.0)
    elo = db.Column(db.Integer, default=1200)
    rank = db.Column(db.Integer)

    def __repr__(self):
        return '<Player %r>' % self.name

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_1_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    player_2_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    player_3_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    player_4_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    winner = db.Column(db.String(20), nullable=False)
    p1_game_score = db.Column(db.Integer, nullable=False, default=0)
    p2_game_score = db.Column(db.Integer, nullable=False, default=0)
    p3_game_score = db.Column(db.Integer, nullable=False, default=0)
    p4_game_score = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return '<Match %r vs %r and %r vs %r>' % (self.player_1_id, self.player_3_id, self.player_2_id, self.player_4_id)

db.create_all()

@app.route('/result')
def result():
    p1 = aliased(Player)
    p2 = aliased(Player)
    p3 = aliased(Player)
    p4 = aliased(Player)
    
    matches = db.session.query(
        Match.id,
        Match.p1_game_score,
        Match.p2_game_score,
        Match.p3_game_score,
        Match.p4_game_score,
        p1.name.label('player_1_name'),
        p2.name.label('player_2_name'),
        p3.name.label('player_3_name'),
        p4.name.label('player_4_name'),
        Match.winner
    ).join(p1, Match.player_1_id == p1.id).\
    join(p2, Match.player_2_id == p2.id).\
    join(p3, Match.player_3_id == p3.id).\
    join(p4, Match.player_4_id == p4.id).all()

    return render_template('result.html', matches=matches)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/add_player', methods=['GET', 'POST'])
def add_player():
    if request.method == 'POST':
        name = request.form['name']
        player = Player(name=name)
        db.session.add(player)
        db.session.commit()
        return redirect(url_for('add_player'))
    else:
        players = Player.query.order_by(Player.name).all()
        return render_template('add_player.html', players=players)


def update_elo_ratings(winner_1, winner_2, loser_1, loser_2, winner_score, loser_score):
    # Award each player 20 basic points for playing the match
    winner_1.elo += 2
    winner_2.elo += 2
    loser_1.elo += 2
    loser_2.elo += 2


    # Calculate the expected scores of the winning and losing teams
    winner_expected_score = 1 / (1 + 10 ** ((loser_1.elo + loser_2.elo - winner_1.elo - winner_2.elo) / 400))
    loser_expected_score = 1 - winner_expected_score

    # Calculate the actual scores of the winning and losing teams
    winner_actual_score = float(winner_score) / (float(winner_score) + float(loser_score))
    loser_actual_score = 1 - winner_actual_score

    # Adjust the ELO rating changes based on the difference between the actual and expected scores
    winner_1.elo += 32 * (winner_actual_score - winner_expected_score)
    winner_2.elo += 32 * (winner_actual_score - winner_expected_score)
    loser_1.elo += 32 * (loser_actual_score - loser_expected_score)
    loser_2.elo += 32 * (loser_actual_score - loser_expected_score)

    # Update the win and loss counts and win rates of the players
    winner_1.wins += 1
    winner_2.wins += 1
    loser_1.losses += 1
    loser_2.losses += 1

    for player in [winner_1, winner_2, loser_1, loser_2]:
        if player.losses == 0:
            player.win_rate = 1.0
        else:
            player.win_rate = player.wins / (player.wins + player.losses)

    db.session.commit()

@app.route('/add_match', methods=['GET', 'POST'])
def add_match():
    if request.method == 'POST':
        player_1_id = request.form['player1']
        player_2_id = request.form['player2']
        player_3_id = request.form['player3']
        player_4_id = request.form['player4']
        winner = request.form['winner']
        p1_game_score = request.form['team1_game_score']
        p2_game_score = request.form['team1_game_score']
        p3_game_score = request.form['team2_game_score']
        p4_game_score = request.form['team2_game_score']

        # Query the database to get the player objects
        player_1 = Player.query.get(player_1_id)
        player_2 = Player.query.get(player_2_id)
        player_3 = Player.query.get(player_3_id)
        player_4 = Player.query.get(player_4_id)

        # Update the ELO ratings and win/loss records based on the winner of the match
        if winner == "1":
            winner_score = p1_game_score
            loser_score = p3_game_score
            update_elo_ratings(player_1, player_2, player_3, player_4, winner_score, loser_score)
        else:
            winner_score = p3_game_score
            loser_score = p1_game_score
            update_elo_ratings(player_3, player_4, player_1, player_2, loser_score, winner_score)

        # Create a new Match object and add it to the database
        match = Match(player_1_id=player_1_id, player_2_id=player_2_id, player_3_id=player_3_id, player_4_id=player_4_id, winner=winner, p1_game_score=p1_game_score, p2_game_score=p2_game_score, p3_game_score=p3_game_score, p4_game_score=p4_game_score)
        db.session.add(match)
        db.session.commit()

        return redirect(url_for('add_match'))
    else:
        players = Player.query.order_by(Player.name).all()
        return render_template('add_match.html', players=players)

@app.route('/leaderboard')
def leaderboard():
    players = Player.query.order_by(Player.elo.desc()).all()
    for i, player in enumerate(players):
        player.rank = i + 1
    db.session.commit()
    return render_template('leaderboard.html', players=players)

if __name__ == '__main__':
    db.create_all()
    app.run(port= 5000, debug=False)