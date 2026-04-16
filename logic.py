import json


# --- 1. SUPPORTING CLASSES ---
class TimeSlot:
    """Represents a block of time, such as 'Monday 3-4 PM'."""
    def __init__(self, day, start_time, end_time):
        self.day = day.strip().capitalize()
        self.start_time = int(start_time)
        self.end_time = int(end_time)

    def overlaps(self, other):
        """Checks whether two time slots overlap."""
        if self.day != other.day:
            return False
        return self.start_time < other.end_time and self.end_time > other.start_time

    def get_overlap(self, other):
        """Returns the exact overlapping TimeSlot, or None if no overlap."""
        if not self.overlaps(other):
            return None

        overlap_start = max(self.start_time, other.start_time)
        overlap_end = min(self.end_time, other.end_time)
        return TimeSlot(self.day, overlap_start, overlap_end)

    def to_dict(self):
        return {
            "day": self.day,
            "start": self.start_time,
            "end": self.end_time
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["day"], data["start"], data["end"])

    def __str__(self):
        return f"{self.day} {self.start_time}:00-{self.end_time}:00"


class MatchRecord:
    """Stores one confirmed study match."""
    def __init__(self, student1, student2, time_slot):
        self.student1 = student1
        self.student2 = student2
        self.time_slot = time_slot

    def involves(self, student_name):
        return self.student1 == student_name or self.student2 == student_name

    def to_dict(self):
        return {
            "student1": self.student1,
            "student2": self.student2,
            "time_slot": self.time_slot.to_dict()
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["student1"],
            data["student2"],
            TimeSlot.from_dict(data["time_slot"])
        )

    def __str__(self):
        return f"{self.student1} matched with {self.student2} on {self.time_slot}"


class Student:
    """Represents one student and their history."""
    def __init__(self, student_id, name, usage_count=0):
        self.student_id = student_id
        self.name = name
        self.availability = []
        self.usage_count = usage_count

    def add_availability(self, time_slot):
        self.availability.append(time_slot)

    def is_available(self, requested_slot):
        return any(slot.overlaps(requested_slot) for slot in self.availability)

    def get_matching_slot(self, requested_slot):
        """Returns the first exact overlapping slot with the requested slot."""
        for slot in self.availability:
            overlap = slot.get_overlap(requested_slot)
            if overlap:
                return overlap
        return None

    def get_all_overlaps(self, other_student):
        """Returns all exact overlapping time slots with another student."""
        overlaps = []

        for my_slot in self.availability:
            for other_slot in other_student.availability:
                overlap = my_slot.get_overlap(other_slot)
                if overlap:
                    overlaps.append(overlap)

        return overlaps

    def get_overlap_text(self, other_student):
        overlaps = self.get_all_overlaps(other_student)
        if not overlaps:
            return "No matching time"
        return ", ".join(str(slot) for slot in overlaps)

    def increment_usage(self):
        self.usage_count += 1


class StudyRequest:
    """Stores one study request and the ordered candidate list."""
    def __init__(self, request_id, requester, time_slot, candidate_names, candidate_slots,
                 current_index=0, status="open"):
        self.request_id = request_id
        self.requester = requester
        self.time_slot = time_slot
        self.candidate_names = candidate_names
        self.candidate_slots = candidate_slots
        self.current_index = current_index
        self.status = status

    def has_next_candidate(self):
        return self.current_index < len(self.candidate_names)

    def get_current_candidate_name(self):
        if self.has_next_candidate():
            return self.candidate_names[self.current_index]
        return None

    def get_current_candidate_slot(self):
        if self.has_next_candidate():
            return self.candidate_slots[self.current_index]
        return None

    def move_to_next_candidate(self):
        self.current_index += 1

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "requester": self.requester,
            "time_slot": self.time_slot.to_dict(),
            "candidate_names": self.candidate_names,
            "candidate_slots": [slot.to_dict() for slot in self.candidate_slots],
            "current_index": self.current_index,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["request_id"],
            data["requester"],
            TimeSlot.from_dict(data["time_slot"]),
            data.get("candidate_names", []),
            [TimeSlot.from_dict(slot) for slot in data.get("candidate_slots", [])],
            data.get("current_index", 0),
            data.get("status", "open")
        )


class Invitation:
    """Stores one invitation sent to one invitee."""
    def __init__(self, invitation_id, request_id, requester, invitee, time_slot, status="pending"):
        self.invitation_id = invitation_id
        self.request_id = request_id
        self.requester = requester
        self.invitee = invitee
        self.time_slot = time_slot
        self.status = status

    def to_dict(self):
        return {
            "invitation_id": self.invitation_id,
            "request_id": self.request_id,
            "requester": self.requester,
            "invitee": self.invitee,
            "time_slot": self.time_slot.to_dict(),
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["invitation_id"],
            data["request_id"],
            data["requester"],
            data["invitee"],
            TimeSlot.from_dict(data["time_slot"]),
            data.get("status", "pending")
        )


# --- 2. DATA STORAGE ---
class DataStore:
    """Handles saving and loading data via JSON."""
    FILE_NAME = "study_data.json"

    def save(self, students, match_history, study_requests, invitations):
        data = {
            "students": [],
            "matches": [],
            "study_requests": [],
            "invitations": []
        }

        for s in students:
            slots = [t.to_dict() for t in s.availability]
            data["students"].append({
                "id": s.student_id,
                "name": s.name,
                "usage": s.usage_count,
                "avail": slots
            })

        for match in match_history:
            data["matches"].append(match.to_dict())

        for req in study_requests:
            data["study_requests"].append(req.to_dict())

        for inv in invitations:
            data["invitations"].append(inv.to_dict())

        with open(self.FILE_NAME, "w") as f:
            json.dump(data, f, indent=4)

    def load(self):
        try:
            with open(self.FILE_NAME, "r") as f:
                data = json.load(f)

            students = []
            match_history = []
            study_requests = []
            invitations = []

            if isinstance(data, dict):
                for d in data.get("students", []):
                    s = Student(d["id"], d["name"], d["usage"])
                    for t in d.get("avail", []):
                        s.add_availability(TimeSlot.from_dict(t))
                    students.append(s)

                match_history = [
                    MatchRecord.from_dict(m) for m in data.get("matches", [])
                ]

                study_requests = [
                    StudyRequest.from_dict(r) for r in data.get("study_requests", [])
                ]

                invitations = [
                    Invitation.from_dict(i) for i in data.get("invitations", [])
                ]

                return students, match_history, study_requests, invitations

            elif isinstance(data, list):
                for d in data:
                    s = Student(d["id"], d["name"], d["usage"])
                    for t in d.get("avail", []):
                        s.add_availability(TimeSlot(t["day"], t["start"], t["end"]))
                    students.append(s)

                return students, [], [], []

        except (FileNotFoundError, json.JSONDecodeError):
            return [], [], [], []


# --- 3. MATCHING LOGIC ---
class Matcher:
    def find_matches(self, requester, time_slot, all_students):
        candidates = [
            s for s in all_students
            if s.name != requester.name and s.is_available(time_slot)
        ]

        candidates.sort(key=lambda x: x.usage_count)

        results = []
        for partner in candidates:
            overlap = partner.get_matching_slot(time_slot)
            if overlap:
                results.append((partner, overlap))

        return results

    def confirm_match(self, requester, partner, time_slot, match_history):
        requester.increment_usage()
        partner.increment_usage()

        match = MatchRecord(requester.name, partner.name, time_slot)
        match_history.append(match)


# --- 4. MAIN APPLICATION ---
class SilentStudyApp:
    """The main system runner."""
    def __init__(self):
        self.store = DataStore()
        self.matcher = Matcher()
        self.students, self.match_history, self.study_requests, self.invitations = self.store.load()
        self.current_user = None

    def save_all(self):
        self.store.save(
            self.students,
            self.match_history,
            self.study_requests,
            self.invitations
        )

    def get_student_by_name(self, name):
        for student in self.students:
            if student.name.lower() == name.lower():
                return student
        return None

    def get_request_by_id(self, request_id):
        for req in self.study_requests:
            if req.request_id == request_id:
                return req
        return None

    def get_invitation_by_id(self, invitation_id):
        for inv in self.invitations:
            if inv.invitation_id == invitation_id:
                return inv
        return None

    def get_next_request_id(self):
        return str(len(self.study_requests) + 1)

    def get_next_invitation_id(self):
        return str(len(self.invitations) + 1)

    def create_study_request(self, requester, time_slot):
        matches = self.matcher.find_matches(requester, time_slot, self.students)

        if not matches:
            return None, None

        candidate_names = [partner.name for partner, _ in matches]
        candidate_slots = [slot for _, slot in matches]

        request_obj = StudyRequest(
            request_id=self.get_next_request_id(),
            requester=requester.name,
            time_slot=time_slot,
            candidate_names=candidate_names,
            candidate_slots=candidate_slots,
            current_index=0,
            status="open"
        )

        self.study_requests.append(request_obj)

        invitation = self.send_next_invitation(request_obj)

        self.save_all()
        return request_obj, invitation

    def send_next_invitation(self, request_obj):
        if not request_obj.has_next_candidate():
            request_obj.status = "closed"
            self.save_all()
            return None

        invitee_name = request_obj.get_current_candidate_name()
        invitee_slot = request_obj.get_current_candidate_slot()

        invitation = Invitation(
            invitation_id=self.get_next_invitation_id(),
            request_id=request_obj.request_id,
            requester=request_obj.requester,
            invitee=invitee_name,
            time_slot=invitee_slot,
            status="pending"
        )

        self.invitations.append(invitation)
        self.save_all()
        return invitation

    def accept_invitation(self, invitation_id):
        invitation = self.get_invitation_by_id(invitation_id)
        if not invitation or invitation.status != "pending":
            return False

        request_obj = self.get_request_by_id(invitation.request_id)
        if not request_obj:
            return False

        requester = self.get_student_by_name(invitation.requester)
        invitee = self.get_student_by_name(invitation.invitee)

        if not requester or not invitee:
            return False

        invitation.status = "accepted"
        request_obj.status = "matched"

        self.matcher.confirm_match(
            requester,
            invitee,
            invitation.time_slot,
            self.match_history
        )

        self.save_all()
        return True

    def reject_invitation(self, invitation_id):
        invitation = self.get_invitation_by_id(invitation_id)
        if not invitation or invitation.status != "pending":
            return None

        request_obj = self.get_request_by_id(invitation.request_id)
        if not request_obj:
            return None

        invitation.status = "rejected"
        request_obj.move_to_next_candidate()

        if request_obj.has_next_candidate():
            new_invitation = self.send_next_invitation(request_obj)
            self.save_all()
            return new_invitation
        else:
            request_obj.status = "closed"
            self.save_all()
            return None

    def get_received_invitations(self, student_name):
        return [
            inv for inv in self.invitations
            if inv.invitee == student_name
        ]

    def get_sent_invitations(self, student_name):
        return [
            inv for inv in self.invitations
            if inv.requester == student_name
        ]


