from utils.misc import get_ip_address, reverse_tournament
from utils.tables import TabbycatTableBuilder

from .models import Submission


class TabroomSubmissionFieldsMixin:
    """Mixin that provides retrieval of appropriate fields for the Submission
    instance, used with forms that are submitted by tabroom officials. It is up
    to subclasses to use get_submitter_fields() appropriately."""

    def get_submitter_fields(self):
        return {
            'submitter': self.request.user,
            'submitter_type': Submission.SUBMITTER_TABROOM,
            'ip_address': get_ip_address(self.request)
        }


class PublicSubmissionFieldsMixin:
    """Mixin that provides retrieval of appropriate fields for the Submission
    instance, used with forms that are submitted from the public pages. It is up
    to subclasses to use get_submitter_fields() appropriately."""

    def get_submitter_fields(self):
        return {
            'submitter_type': Submission.SUBMITTER_PUBLIC,
            'ip_address': get_ip_address(self.request)
        }


class ResultsTableBuilder(TabbycatTableBuilder):
    """Painfully construct the edit links; this is the only case where
    a cell has multiple links; hence the creating HTML directly"""

    def get_status_meta(self, debate):
        if debate.aff_team.type == 'B' or debate.neg_team.type == 'B':
            return "glyphicon-fast-forward", 5, "Bye Debate"
        elif debate.result_status == debate.STATUS_NONE and not debate.ballot_in:
            return "glyphicon-remove text-danger", 0, "No Ballot"
        elif debate.result_status == debate.STATUS_NONE and debate.ballot_in:
            return "glyphicon-inbox text-warning", 1, "Ballot is In"
        elif debate.result_status == debate.STATUS_DRAFT:
            return "glyphicon-adjust text-info", 2, "Ballot is Unconfirmed"
        elif debate.result_status == debate.STATUS_CONFIRMED:
            return "glyphicon-ok text-success", 3, "Ballot is Confirmed"
        elif debate.result_status == debate.STATUS_POSTPONED:
            return "glyphicon-pause", 4, "Debate was Postponed"
        else:
            raise ValueError('Debate has no discernable status')

    def add_ballot_status_columns(self, debates, key="Status"):

        status_header = {
            'key': key,
            'tooltip': "Status of this debate's ballot",
            'icon': "glyphicon-th-list",
        }
        status_cell = [{
            'icon': self.get_status_meta(debate)[0],
            'sort': self.get_status_meta(debate)[1],
            'tooltip': self.get_status_meta(debate)[2]
        } for debate in debates]
        self.add_column(status_header, status_cell)

    def get_ballot_text(self, debate):
        ballotsets_info = " "

        # These are prefetched, so sort using Python rather than generating an SQL query
        ballotsubmissions = sorted(debate.ballotsubmission_set.all(), key=lambda x: x.version)

        for ballotset in ballotsubmissions:
            link = reverse_tournament('edit_ballotset',
                                      self.tournament,
                                      kwargs={'ballotsub_id': ballotset.id})
            ballotsets_info = "<a href=" + link + ">"
            if ballotset.confirmed:
                edit_status = "Re-edit v" + str(ballotset.version)
            elif self.admin:
                edit_status = "Edit v" + str(ballotset.version)
            else:
                edit_status = "Review v" + str(ballotset.version)
            if ballotset.discarded:
                ballotsets_info += "<strike class='text-muted'>" + edit_status + "</strike></a><small> discarded; "
            else:
                ballotsets_info += edit_status + "</a><small> "

            if ballotset.submitter_type == ballotset.SUBMITTER_TABROOM:
                ballotsets_info += " <em>entered by " + ballotset.submitter.username + "</em></small><br>"
            elif ballotset.submitter_type == ballotset.SUBMITTER_PUBLIC:
                ballotsets_info += " <em>a public submission by " + ballotset.ip_address + "</em></small><br>"

        if all(x.discarded for x in ballotsubmissions):
            link = reverse_tournament('new_ballotset',
                                      self.tournament,
                                      kwargs={'debate_id': debate.id})
            ballotsets_info += "<a href=" + link + ">Enter Ballot</a>"

        return ballotsets_info

    def add_ballot_entry_columns(self, debates):

        entry_header = {'key': 'EB', 'icon': "glyphicon-plus"}
        entry_cells = [{'text': self.get_ballot_text(d)} for d in debates]
        self.add_column(entry_header, entry_cells)

        if self.tournament.pref('enable_postponements'):
            postpones_header = {'key': 'Postpone'}
            postpones_cells = [{
                'text': 'Un-Postpone' if d.result_status == d.STATUS_POSTPONED else 'Postpone',
                'link': reverse_tournament('toggle_postponed', self.tournament, kwargs={'debate_id': d.id})
            } for d in debates]
            self.add_column(postpones_header, postpones_cells)
