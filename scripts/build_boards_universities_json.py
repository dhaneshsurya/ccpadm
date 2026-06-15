"""Build static/data/india_boards_universities.json for admission form."""
import json
import urllib.request
from pathlib import Path

SCHOOL_BOARDS = [
    # National boards
    'CBSE - Central Board of Secondary Education',
    'ICSE / CISCE - Council for the Indian School Certificate Examinations',
    'NIOS - National Institute of Open Schooling',
    # State & UT school / higher secondary boards
    'Andhra Pradesh Board of Secondary Education (BSEAP)',
    'Andhra Pradesh Board of Intermediate Education (BIEAP)',
    'Arunachal Pradesh Board of Secondary Education (APBSE)',
    'Assam Board of Secondary Education (SEBA)',
    'Assam Higher Secondary Education Council (AHSEC)',
    'Bihar School Examination Board (BSEB)',
    'Chhattisgarh Board of Secondary Education (CGBSE)',
    'Goa Board of Secondary and Higher Secondary Education (GBSHSE)',
    'Gujarat Secondary and Higher Secondary Education Board (GSEB)',
    'Board of School Education Haryana (BSEH / HBSE)',
    'Himachal Pradesh Board of School Education (HPBOSE)',
    'Jammu and Kashmir State Board of School Education (JKBOSE)',
    'Jharkhand Academic Council (JAC)',
    'Karnataka Secondary Education Examination Board (KSEEB)',
    'Kerala Board of Public Examinations (KBPE)',
    'Kerala Department of Higher Secondary Education (DHSE)',
    'Madhya Pradesh Board of Secondary Education (MPBSE)',
    'Maharashtra State Board of Secondary and Higher Secondary Education (MSBSHSE)',
    'Board of Secondary Education, Manipur (BSEM)',
    'Council of Higher Secondary Education, Manipur (COHSEM)',
    'Meghalaya Board of School Education (MBOSE)',
    'Mizoram Board of School Education (MBSE)',
    'Nagaland Board of School Education (NBSE)',
    'Board of Secondary Education, Odisha (BSE Odisha)',
    'Council of Higher Secondary Education, Odisha (CHSE Odisha)',
    'Punjab School Education Board (PSEB)',
    'Board of Secondary Education, Rajasthan (RBSE)',
    'Sikkim Board of School Education (SBOSE)',
    'Tamil Nadu State Board (TNBSE)',
    'Telangana Board of Secondary Education (BSE Telangana)',
    'Telangana State Board of Intermediate Education (TSBIE)',
    'Tripura Board of Secondary Education (TBSE)',
    'Uttar Pradesh Madhyamik Shiksha Parishad (UPMSP)',
    'Uttarakhand Board of School Education (UBSE)',
    'West Bengal Board of Secondary Education (WBBSE)',
    'West Bengal Council of Higher Secondary Education (WBCHSE)',
    'Central Tibetan Schools Administration (CTSA)',
    'Other School Board',
]

CHHATTISGARH_UNIVERSITIES = [
    'Atal Bihari Vajpayee Vishwavidyalaya, Bilaspur, Chhattisgarh',
    'Shaheed Nandkumar Patel Vishwavidyalaya, Raigarh, Chhattisgarh',
    'Pandit Ravishankar Shukla University, Raipur, Chhattisgarh',
    'Guru Ghasidas Vishwavidyalaya, Bilaspur, Chhattisgarh',
    'Indira Gandhi Krishi Vishwavidyalaya, Raipur, Chhattisgarh',
    'Chhattisgarh Swami Vivekanand Technical University, Bhilai, Chhattisgarh',
    'Hidayatullah National Law University, Raipur, Chhattisgarh',
    'Ayush and Health Sciences University of Chhattisgarh, Raipur',
    'Chhattisgarh Kamdhenu Vishwavidyalaya, Raipur, Chhattisgarh',
    'Pandit Sundarlal Sharma Open University, Bilaspur, Chhattisgarh',
    'Kushabhau Thakre Patrakarita Avam Jansanchar University, Raipur, Chhattisgarh',
    'Dr. C.V. Raman University, Bilaspur, Chhattisgarh',
    'ICFAI University, Raipur, Chhattisgarh',
    'ITM University, Raipur, Chhattisgarh',
    'Kalinga University, Raipur, Chhattisgarh',
    'MATS University, Raipur, Chhattisgarh',
    'O.P. Jindal University, Raipur, Chhattisgarh',
    'Amity University, Raipur, Chhattisgarh',
    'Maharishi University of Management and Technology, Chhattisgarh',
    'Shri Rawatpura Sarkar University, Raipur, Chhattisgarh',
    'G.H. Raisoni University, Chhattisgarh',
    'Bhartiya Skill Development University, Chhattisgarh',
    'National Institute of Technology, Raipur, Chhattisgarh',
    'Indian Institute of Technology, Bhilai, Chhattisgarh',
    'All India Institute of Medical Sciences, Raipur, Chhattisgarh',
]

EXTRA_UNIVERSITIES = [
    'Indira Gandhi National Open University (IGNOU)',
    'University of Delhi',
    'Banaras Hindu University (BHU)',
    'Aligarh Muslim University (AMU)',
    'Jamia Millia Islamia',
    'Jawaharlal Nehru University (JNU)',
    'Other University',
]

CG_ALIASES = {
    'atal bihari vajpayee vishwavidyalaya': 'Atal Bihari Vajpayee Vishwavidyalaya, Bilaspur, Chhattisgarh',
    'shaheed nandkumar patel vishwavidyalaya': 'Shaheed Nandkumar Patel Vishwavidyalaya, Raigarh, Chhattisgarh',
    'shaheed nandkumar patel vishwvidyalaya': 'Shaheed Nandkumar Patel Vishwavidyalaya, Raigarh, Chhattisgarh',
}


def normalize_cg_name(name):
    key = name.lower().strip()
    for fragment, canonical in CG_ALIASES.items():
        if fragment in key:
            return canonical
    if 'chhattisgarh' in key or 'bilaspur' in key or 'raigarh' in key or 'raipur' in key:
        for cg in CHHATTISGARH_UNIVERSITIES:
            if name.lower() in cg.lower() or cg.lower() in name.lower():
                return cg
    return name.strip()


def fetch_india_universities():
    url = (
        'https://raw.githubusercontent.com/Hipo/university-domains-list/'
        'master/world_universities_and_domains.json'
    )
    with urllib.request.urlopen(url, timeout=60) as response:
        data = json.loads(response.read())

    cg_set = {u.lower() for u in CHHATTISGARH_UNIVERSITIES}
    others = set()
    for item in data:
        if item.get('country') != 'India':
            continue
        name = item['name'].strip()
        if name.lower() in cg_set:
            continue
        if any(cg.lower() in name.lower() for cg in CHHATTISGARH_UNIVERSITIES):
            continue
        others.add(name)

    for name in EXTRA_UNIVERSITIES:
        others.add(name)

    return sorted(others, key=str.lower)


def main():
    out = Path(__file__).resolve().parents[1] / 'static' / 'data' / 'india_boards_universities.json'
    chhattisgarh = sorted(set(CHHATTISGARH_UNIVERSITIES), key=str.lower)
    payload = {
        'school_boards': sorted(set(SCHOOL_BOARDS), key=str.lower),
        'chhattisgarh_universities': chhattisgarh,
        'universities': fetch_india_universities(),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Wrote {out}')
    print(f"School boards: {len(payload['school_boards'])}")
    print(f"Chhattisgarh universities: {len(payload['chhattisgarh_universities'])}")
    print(f"Other universities: {len(payload['universities'])}")


if __name__ == '__main__':
    main()