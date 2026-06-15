"""
Import data from existing SQL Server databases (ccpdb + courseinformation)
into Django SQLite models.

Usage:
    python manage.py import_from_sqlserver
    python manage.py import_from_sqlserver --clear
    python manage.py import_from_sqlserver --server .\\SQLEXPRESS
"""

import uuid
from datetime import datetime

import pyodbc
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import AdminUser, PasswordResetOTP, Student
from admissions.models import StudentAdmission, StudentDocument, StudentEducation
from courses.models import AcademicSession, College, Program, ProgramCourse


def make_connection(server, database, trusted=True):
    if trusted:
        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={server};DATABASE={database};'
            f'Trusted_Connection=yes;'
        )
    else:
        raise NotImplementedError('SQL auth not configured. Use Trusted_Connection.')
    return pyodbc.connect(conn_str)


def parse_datetime(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        dt = val
        if timezone.is_naive(dt):
            return timezone.make_aware(dt)
        return dt
    return None


def parse_date(val):
    if val is None:
        return None
    if hasattr(val, 'year'):
        return val
    return None


def parse_uuid(val):
    if not val:
        return uuid.uuid4()
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return uuid.uuid4()


class Command(BaseCommand):
    help = 'Import data from SQL Server ccpdb and courseinformation databases'

    def add_arguments(self, parser):
        parser.add_argument('--server', default=settings.MSSQL_SERVER)
        parser.add_argument('--ccpdb', default=settings.MSSQL_CCPDB)
        parser.add_argument('--coursedb', default=settings.MSSQL_COURSEDB)
        parser.add_argument('--clear', action='store_true', help='Clear Django tables before import')

    def handle(self, *args, **options):
        server = options['server']
        ccpdb = options['ccpdb']
        coursedb = options['coursedb']

        if options['clear']:
            self.stdout.write('Clearing existing Django data...')
            StudentAdmission.objects.all().delete()
            StudentEducation.objects.all().delete()
            StudentDocument.objects.all().delete()
            Student.objects.all().delete()
            AdminUser.objects.all().delete()
            PasswordResetOTP.objects.all().delete()
            ProgramCourse.objects.all().delete()
            Program.objects.all().delete()
            College.objects.all().delete()
            AcademicSession.objects.all().delete()

        with transaction.atomic():
            self._import_courses(server, coursedb)
            self._import_ccpdb(server, ccpdb)

        self.stdout.write(self.style.SUCCESS('Import completed successfully.'))

    def _import_courses(self, server, database):
        self.stdout.write(f'Importing from {database}...')
        conn = make_connection(server, database)
        cursor = conn.cursor()

        for row in cursor.execute('SELECT SessionID, SessionName, IsActive FROM AcademicSessions'):
            AcademicSession.objects.update_or_create(
                legacy_id=row.SessionID,
                defaults={'session_name': row.SessionName, 'is_active': bool(row.IsActive)},
            )

        for row in cursor.execute('SELECT CollegeID, CollegeName, Code FROM Colleges'):
            College.objects.update_or_create(
                legacy_id=row.CollegeID,
                defaults={'college_name': row.CollegeName, 'code': row.Code or ''},
            )

        for row in cursor.execute(
            'SELECT ProgramID, ProgramCode, ProgramName, ProgramLevel, IsNEPCompliant, IsActive FROM Programs'
        ):
            Program.objects.update_or_create(
                legacy_id=row.ProgramID,
                defaults={
                    'program_code': row.ProgramCode or '',
                    'program_name': row.ProgramName,
                    'program_level': row.ProgramLevel or '',
                    'is_nep_compliant': row.IsNEPCompliant,
                    'is_active': bool(row.IsActive) if row.IsActive is not None else True,
                },
            )

        for row in cursor.execute(
            '''SELECT ID, ProgramType, CourseName, Course_Type_1, Course_Type_2,
                      SortOrder, CreatedBy, CreatedDate, ModifiedBy, ModifiedDate
               FROM Program_Courses'''
        ):
            ProgramCourse.objects.update_or_create(
                legacy_id=row.ID,
                defaults={
                    'program_type': row.ProgramType or '',
                    'course_name': row.CourseName or '',
                    'course_type_1': row.Course_Type_1 or '',
                    'course_type_2': row.Course_Type_2 or '',
                    'sort_order': row.SortOrder,
                    'created_by': row.CreatedBy or '',
                    'created_date': parse_datetime(row.CreatedDate),
                    'modified_by': row.ModifiedBy or '',
                    'modified_date': parse_datetime(row.ModifiedDate),
                },
            )

        conn.close()
        self.stdout.write(f'  Program_Courses: {ProgramCourse.objects.count()} records')

    def _import_ccpdb(self, server, database):
        self.stdout.write(f'Importing from {database}...')
        conn = make_connection(server, database)
        cursor = conn.cursor()

        for row in cursor.execute(
            '''SELECT Id, FullName, Email, Mobile, Password, IsVerified, Aadhaar,
                      UserId, ProgramType, CourseName, CreatedDate, RegistrationNo
               FROM Students'''
        ):
            Student.objects.update_or_create(
                registration_no=row.RegistrationNo,
                defaults={
                    'legacy_id': row.Id,
                    'full_name': row.FullName or '',
                    'email': row.Email or '',
                    'mobile': row.Mobile or '',
                    'password': row.Password or '',
                    'is_verified': bool(row.IsVerified) if row.IsVerified is not None else False,
                    'aadhaar': row.Aadhaar or '',
                    'user_id': parse_uuid(row.UserId),
                    'program_type': row.ProgramType or '',
                    'course_name': row.CourseName or '',
                    'created_date': parse_datetime(row.CreatedDate) or timezone.now(),
                },
            )

        for row in cursor.execute('SELECT Id, Username, Password, ResetKey FROM AdminUsers'):
            AdminUser.objects.update_or_create(
                username=row.Username,
                defaults={
                    'legacy_id': row.Id,
                    'password': row.Password or '',
                    'reset_key': row.ResetKey,
                },
            )

        for row in cursor.execute(
            '''SELECT OTPId, Email, OTPHash, CreatedAt, ExpiryAt, Attempts, IsUsed
               FROM PasswordResetOTP'''
        ):
            PasswordResetOTP.objects.update_or_create(
                legacy_id=row.OTPId,
                defaults={
                    'email': row.Email,
                    'otp_hash': row.OTPHash,
                    'created_at': parse_datetime(row.CreatedAt) or timezone.now(),
                    'expiry_at': parse_datetime(row.ExpiryAt) or timezone.now(),
                    'attempts': row.Attempts or 0,
                    'is_used': bool(row.IsUsed),
                },
            )

        admission_sql = '''
            SELECT Id, ApplicationNo, RegNo, ProgramType, CourseName, Subject,
                   FullName, FatherName, MotherName, Gender, Category, Nationality,
                   Religion, MaritalStatus, BloodGroup, DOB, Mobile, Email, Aadhaar,
                   APAARId, HasDisability, DisabilityDetails, DisabilityPercentage,
                   DisabilityType, IsMinority, Medium,
                   PermState, PermDistrict, PermCity, PermVillage, PermPinCode,
                   CorrState, CorrDistrict, CorrCity, CorrVillage, CorrPinCode,
                   Class10, Board10, Duration10, Year10, TotalMarks10, Obtained10,
                   Percentage10, Grade10, Class12, Board12, Duration12, Year12,
                   TotalMarks12, Obtained12, Percentage12, Grade12,
                   ClassGrad, BoardGrad, DurationGrad, YearGrad, TotalMarksGrad,
                   ObtainedGrad, PercentageGrad, GradeGrad,
                   PhotoBase64, SignatureBase64, SelectedSubjectsJson,
                   Status, IsSubmitted, IsApproved, IsRejected, Remarks,
                   ApprovedBy, ApprovedDate, RejectedBy, RejectedDate,
                   CreatedDate, UpdatedDate, SubmittedDate
            FROM StudentAdmission
        '''
        for row in cursor.execute(admission_sql):
            lookup = {}
            if row.ApplicationNo:
                lookup['application_no'] = row.ApplicationNo
            else:
                lookup['legacy_id'] = row.Id

            defaults = {
                'legacy_id': row.Id,
                'application_no': row.ApplicationNo,
                'reg_no': row.RegNo or '',
                'program_type': row.ProgramType or '',
                'course_name': row.CourseName or '',
                'subject': row.Subject or '',
                'full_name': row.FullName or '',
                'father_name': row.FatherName or '',
                'mother_name': row.MotherName or '',
                'gender': row.Gender or '',
                'category': row.Category or '',
                'nationality': row.Nationality or '',
                'religion': row.Religion or '',
                'marital_status': row.MaritalStatus or '',
                'blood_group': row.BloodGroup or '',
                'dob': parse_date(row.DOB),
                'mobile': row.Mobile or '',
                'email': row.Email or '',
                'aadhaar': row.Aadhaar or '',
                'apaar_id': row.APAARId or '',
                'has_disability': row.HasDisability,
                'disability_details': row.DisabilityDetails or '',
                'disability_percentage': row.DisabilityPercentage or '',
                'disability_type': row.DisabilityType or '',
                'is_minority': row.IsMinority,
                'medium': row.Medium or '',
                'perm_state': row.PermState or '',
                'perm_district': row.PermDistrict or '',
                'perm_city': row.PermCity or '',
                'perm_village': row.PermVillage or '',
                'perm_pin_code': row.PermPinCode or '',
                'corr_state': row.CorrState or '',
                'corr_district': row.CorrDistrict or '',
                'corr_city': row.CorrCity or '',
                'corr_village': row.CorrVillage or '',
                'corr_pin_code': row.CorrPinCode or '',
                'class10': row.Class10 or '',
                'board10': row.Board10 or '',
                'duration10': row.Duration10,
                'year10': row.Year10,
                'total_marks10': str(row.TotalMarks10 or ''),
                'obtained10': str(row.Obtained10 or ''),
                'percentage10': str(row.Percentage10 or ''),
                'grade10': row.Grade10 or '',
                'class12': row.Class12 or '',
                'board12': row.Board12 or '',
                'duration12': row.Duration12,
                'year12': row.Year12,
                'total_marks12': str(row.TotalMarks12 or ''),
                'obtained12': str(row.Obtained12 or ''),
                'percentage12': str(row.Percentage12 or ''),
                'grade12': row.Grade12 or '',
                'class_grad': row.ClassGrad or '',
                'board_grad': row.BoardGrad or '',
                'duration_grad': row.DurationGrad,
                'year_grad': row.YearGrad,
                'total_marks_grad': str(row.TotalMarksGrad or ''),
                'obtained_grad': str(row.ObtainedGrad or ''),
                'percentage_grad': str(row.PercentageGrad or ''),
                'grade_grad': row.GradeGrad or '',
                'photo_base64': row.PhotoBase64,
                'signature_base64': row.SignatureBase64,
                'selected_subjects_json': row.SelectedSubjectsJson,
                'status': row.Status or 'Draft',
                'is_submitted': row.IsSubmitted,
                'is_approved': row.IsApproved,
                'is_rejected': row.IsRejected,
                'remarks': row.Remarks or '',
                'approved_by': row.ApprovedBy or '',
                'approved_date': parse_datetime(row.ApprovedDate),
                'rejected_by': row.RejectedBy or '',
                'rejected_date': parse_datetime(row.RejectedDate),
                'created_date': parse_datetime(row.CreatedDate),
                'updated_date': parse_datetime(row.UpdatedDate),
                'submitted_date': parse_datetime(row.SubmittedDate),
            }

            if lookup.get('application_no'):
                StudentAdmission.objects.update_or_create(application_no=lookup['application_no'], defaults=defaults)
            else:
                StudentAdmission.objects.update_or_create(legacy_id=lookup['legacy_id'], defaults=defaults)

        for row in cursor.execute(
            '''SELECT Id, ApplicationNo, ExamLevel, ClassName, Board, Duration,
                      YearOfPassing, TotalMarks, MarksObtained, Percentage, Grade
               FROM StudentEducation'''
        ):
            StudentEducation.objects.update_or_create(
                legacy_id=row.Id,
                defaults={
                    'application_no': row.ApplicationNo or '',
                    'exam_level': row.ExamLevel or '',
                    'class_name': row.ClassName or '',
                    'board': row.Board or '',
                    'duration': row.Duration or '',
                    'year_of_passing': row.YearOfPassing or '',
                    'total_marks': row.TotalMarks or '',
                    'marks_obtained': row.MarksObtained or '',
                    'percentage': row.Percentage or '',
                    'grade': row.Grade or '',
                },
            )

        for row in cursor.execute(
            'SELECT DocId, ApplicationNo, PhotoVerified, AadharVerified, SignatureVerified, Status FROM StudentDocuments'
        ):
            StudentDocument.objects.update_or_create(
                legacy_id=row.DocId,
                defaults={
                    'application_no': row.ApplicationNo or '',
                    'photo_verified': row.PhotoVerified,
                    'aadhar_verified': row.AadharVerified,
                    'signature_verified': row.SignatureVerified,
                    'status': row.Status or '',
                },
            )

        conn.close()
        self.stdout.write(f'  Students: {Student.objects.count()}')
        self.stdout.write(f'  StudentAdmission: {StudentAdmission.objects.count()}')
        self.stdout.write(f'  AdminUsers: {AdminUser.objects.count()}')