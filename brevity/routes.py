import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from brevity import app, db, bcrypt
from brevity.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm
from brevity.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required



@app.route("/")
@app.route("/home")
def home():
    posts = Post.query.all()
    return render_template("home.html", posts = posts)



@app.route("/about")
def about():
    return render_template("about.html", title = "About")


@app.route("/register", methods=['GET', 'POST'])                       #methods=['POST'] to allow POST request also
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f"Your account has been created! You are now able to log in", "success")
        return redirect(url_for('login'))
    return render_template("register.html", title="Register", form = form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home')) 
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template("login.html", title="Login", form = form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))



def save_picture(form_picture):
    random_hex = secrets.token_hex(8)       # To randomize the name of the uploaded image so that the name doesn't collide with the already uploaded ones 
    _, f_ext = os.path.splitext(form_picture.filename)   # Splits the filename and extension in 2 part.
                                            # We don't need the filename. That's why we represent it with '_'.
                                            #     To let the editor know that it's unused.
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static','profile_pics', picture_fn )
    
    output_size = (125,125)
    i = Image.open(form_picture)            # PIL package
    i.thumbnail(output_size)
    i.save(picture_path)
                                            # Delete previous picture while uploading new one.
    prev_picture = os.path.join(app.root_path,'static','profile_pics',current_user.image_file)   
    if os.path.exists(prev_picture) and os.path.basename(prev_picture)!='default.jpg':
        os.remove(prev_picture)
    return picture_fn




@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():           #if the request method is 'POST' then we need to redirect 
                                            #   instead of returning a web page directly.
                                            #   so that when we reload, the form doesn't get resubmitted. (POST/REDIRECT/GET pattern) 
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template("account.html", title = "Account", image_file = image_file, form = form)




@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template("create_post.html", title = "New Post",
                            form = form, legend = 'New Post')




@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id, description = f"There is no post with post id: {post_id}")      
                                                                    #get(id) is used to query the db through Primary key. 
                                                                    #get_or_404(id) to return 404 error instead of None in case of missing entry.
                                                                    #   description to describe the error.
    return render_template('post.html', title=post.title, post=post)





@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template("create_post.html", title = "Update Post",
                            form = form, legend = 'Update Post')





@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))