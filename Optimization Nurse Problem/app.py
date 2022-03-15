
from ortools.sat.python import cp_model
import os
import os.path
from flask_sqlalchemy import SQLAlchemy

from flask import Flask, jsonify, request, render_template,url_for, request,send_from_directory,redirect,flash


app = Flask(__name__)
app.config ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nurses.sqlite3'
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = "random string"


class nurses(db.Model):

    id = db.Column('nurse_id', db.Integer, primary_key = True)

    name = db.Column(db.String(100), nullable = False)

    #email = db.Column(db.String(50), nullable = False, unique = True)

    request = db.Column(db.String(50), default='000000000000000000000')



    def __repr__(self):

        return f"User('{self.name}','{self.request}')"



def schedule(num_nurses,shift_requests,c1,c2,c3,c4,Nurses):
    # This program tries to find an optimal assignment of nurses to shifts
    # (3 shifts per day, for 7 days), subject to some constraints (see below).
    # Each nurse can request to be assigned to specific shifts.
    # The optimal assignment maximizes the number of fulfilled shift requests.
    
    # num_nurses
    # num_shifts
    # num_days
    # nurse_work_together
    # shift_requests
    # Each shift is assigned to at most two nurse in
    # Each nurse works at most two shift per day.
    # Each nurse works at most 8 shifts per week.
    # If a nurse work on night shift the next day she cannot work in morning

    num_shifts = 3
    num_days = 7
    all_nurses = range(num_nurses)
    all_shifts = range(num_shifts)
    all_days = range(num_days)



    #nurse_work_together = [[0, 4]]

    # Creates the model.
    model = cp_model.CpModel()

    # Creates shift variables.
    # shifts[(n, d, s)]: nurse 'n' works shift 's' on day 'd'.
    shifts = {}
    for n in all_nurses:
        for d in all_days:
            for s in all_shifts:
                shifts[(n, d,
                        s)] = model.NewBoolVar('shift_n%id%is%i' % (n, d, s))

    # Each shift is assigned to at most two nurse in .
    for d in all_days:
        for s in all_shifts:
            model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= c1)

    # Each nurse works at most two shift per day.
    for n in all_nurses:
        for d in all_days:
            model.Add(sum(shifts[(n, d, s)] for s in all_shifts) <= c2)
    
    # Each nurse works at most 8 shifts per week.
    for n in all_nurses:
        model.Add(sum(shifts[(n, d, s)] for s in all_shifts for d in all_days) <= c3)

    # If a nurse work on night shift the next day she cannot work in morning
    if c4:
        for n in all_nurses:
            for d in all_days:
                model.AddBoolOr([shifts[(n, d, 2)].Not(), shifts[(n, (d + 1) % 7, 0)].Not()])

    # Try to distribute the shifts evenly, so that each nurse works
    # min_shifts_per_nurse shifts. If this is not possible, because the total
    # number of shifts is not divisible by the number of nurses, some nurses will
    # be assigned one more shift.
    min_shifts_per_nurse = (num_shifts * num_days) // num_nurses
    if num_shifts * num_days % num_nurses == 0:
        max_shifts_per_nurse = min_shifts_per_nurse
    else:
        max_shifts_per_nurse = min_shifts_per_nurse + 1
    for n in all_nurses:
        num_shifts_worked = 0
        for d in all_days:
            for s in all_shifts:
                num_shifts_worked += shifts[(n, d, s)]
        model.Add(min_shifts_per_nurse <= num_shifts_worked)
        model.Add(num_shifts_worked <= max_shifts_per_nurse)

    # pylint: disable=g-complex-comprehension
    model.Maximize(
        sum(shift_requests[n][d][s] * shifts[(n, d, s)] for n in all_nurses
            for d in all_days for s in all_shifts))

    # Creates the solver and solve.
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    sch = []
    shift_name = {0:"Morning",1:"Evening",2:"Night"}
    if status == cp_model.OPTIMAL:
        print('Solution:')
        for d in all_days:
            print('Day', d)
            day=[]
            for n in all_nurses:
                for s in all_shifts:
                    if solver.Value(shifts[(n, d, s)]) == 1:
                        if shift_requests[n][d][s] == 1:
                            day.append([Nurses[n].name,shift_name[s],1])
                            print(Nurses[n].name, 'works shift', shift_name[s], '(requested).')
                        else:
                            day.append([Nurses[n].name,shift_name[s],0])
                            print(Nurses[n].name, 'works shift', shift_name[s],'(not requested).')
            sch.append(day)
            print()
        print(f'Number of shift requests met = {solver.ObjectiveValue()}',f'(out of {num_nurses * min_shifts_per_nurse})')
    else:
        print('No optimal solution found !')

    # Statistics.
    print('\nStatistics')
    print('  - conflicts: %i' % solver.NumConflicts())
    print('  - branches : %i' % solver.NumBranches())
    print('  - wall time: %f s' % solver.WallTime())
    return sch
@app.route("/")
def main():
    return render_template("indexNurse.html")



@app.route("/form")
def form():
    return render_template("form.html")


@app.route("/form2")
def form2():
    Nurses = nurses.query.all()
    return render_template("form2.html")

@app.route("/submit", methods = ['GET', 'POST'])
def submit():
    if request.method == 'POST':
        day1 = request.form.get('day1')
        day2 = request.form.get('day2')
        day3 = request.form.get('day3')
        day4 = request.form.get('day4')
        day5 = request.form.get('day5')
        day6 = request.form.get('day6')
        day7 = request.form.get('day7')


        if not request.form['nursename']:
            flash('Please enter all the fields', 'error')
        else:
            days =[day1,day2,day3,day4,day5,day6,day7]
            l=[[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],[0, 0, 0], [0, 0, 0]]
            for i,day in enumerate(days):
                if day== "Morning":
                    l[i][0]=1
                elif day== "Evening":
                    l[i][1]=1
                elif day == "Night":
                    l[i][2]=1
            #req =[]
            #for x in l:
             #   req.append("".join(map(str,x)))
            #req = "".join(req)
            nur = nurses(name = request.form['nursename'],request = str(l))
            db.session.add(nur)
            db.session.commit()
            flash('Record was successfully added')
            return redirect(url_for('main'))


@app.route("/submit2", methods = ['GET', 'POST'])
def submit2():
    if request.method == 'POST':
        Nurses = nurses.query.all()
        #numshifts = int(request.form['numshifts'])
        #numdays = int(request.form['numdays'])
        #together1 = request.form['together1']
        #together2 = request.form['together2']
        c1 = int(request.form['c1'])
        c2 = int(request.form['c2'])
        c3 = int(request.form['c3'])
        check = request.form.getlist('check')
        if len(check) ==0:
            c4 = False
        else:
            c4 = True
        #print(numshifts)
        #print(numdays)
        #print(together1)
        #print(together2)
        print(c1)
        print(c2)
        print(c3)
        print(check)
        shift_requests=[]
        for n in Nurses:
            shift_requests.append(eval(n.request))
        sc = schedule(len(Nurses),shift_requests,c1,c2,c3,c4,Nurses)
        print(sc)
        day=['','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        return render_template("week.html",sch=sc,days=day)
    return redirect(url_for('main'))




if __name__ == '__main__':
    db.create_all()
    app.run()
