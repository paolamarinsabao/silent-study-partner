from flask import Flask, render_template, request, redirect
from logic import SilentStudyApp, TimeSlot, Student

app = Flask(__name__)

study_app = SilentStudyApp()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"].strip()

        if not name:
            return render_template("login.html")

        study_app.current_user = next(
            (s for s in study_app.students if s.name.lower() == name.lower()),
            None
        )

        if not study_app.current_user:
            study_app.current_user = Student(str(len(study_app.students) + 1), name)
            study_app.students.append(study_app.current_user)

        study_app.save_all()
        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if not study_app.current_user:
        return redirect("/login")

    received_invitations = study_app.get_received_invitations(study_app.current_user.name)
    sent_invitations = study_app.get_sent_invitations(study_app.current_user.name)

    return render_template(
        "dashboard.html",
        students=study_app.students,
        current_user=study_app.current_user,
        matches=study_app.match_history,
        received_invitations=received_invitations,
        sent_invitations=sent_invitations
    )


@app.route("/add_time", methods=["POST"])
def add_time():
    if not study_app.current_user:
        return redirect("/login")

    day = request.form["day"].strip()
    start = int(request.form["start"])
    end = int(request.form["end"])

    if start >= end:
        return redirect("/dashboard")

    slot = TimeSlot(day, start, end)
    study_app.current_user.add_availability(slot)

    study_app.save_all()
    return redirect("/dashboard")


@app.route("/find_matches", methods=["POST"])
def find_matches():
    if not study_app.current_user:
        return redirect("/login")

    day = request.form["day"].strip()
    start = int(request.form["start"])
    end = int(request.form["end"])

    if start >= end:
        return redirect("/dashboard")

    slot = TimeSlot(day, start, end)

    request_obj, invitation = study_app.create_study_request(
        study_app.current_user,
        slot
    )

    if invitation:
        return render_template(
            "matches.html",
            message=f"Invitation sent to {invitation.invitee} for {invitation.time_slot}.",
            invitation=invitation
        )
    else:
        return render_template(
            "matches.html",
            message="No available matches found for that time.",
            invitation=None
        )


@app.route("/accept_invitation", methods=["POST"])
def accept_invitation():
    if not study_app.current_user:
        return redirect("/login")

    invitation_id = request.form["invitation_id"]
    study_app.accept_invitation(invitation_id)

    return redirect("/dashboard")


@app.route("/reject_invitation", methods=["POST"])
def reject_invitation():
    if not study_app.current_user:
        return redirect("/login")

    invitation_id = request.form["invitation_id"]
    study_app.reject_invitation(invitation_id)

    return redirect("/dashboard")


@app.route("/logout")
def logout():
    study_app.current_user = None
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)